import time
import queue
import threading
import json
import uuid
from typing import Any
from core.config import GlobalConfig
from core.logger import StructuredLogger
from workloads.task_a import TaskAAdapter
from workloads.task_b import TaskBAdapter
from core.log_schema import LogEvent, EventType
from core.failure_injection import get_effective_latency, check_crash, CrashSimulationError

class MessageBroker:
    """
    In-memory simulation of a Message Broker (e.g. Redis/RabbitMQ).
    """
    def __init__(self):
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()

def queue_worker_loop(broker: MessageBroker, worker_id: str, config: GlobalConfig, logger: StructuredLogger, run_id: str, trace_id: str, stop_event: threading.Event):
    latency_sec = get_effective_latency(config, worker_id)
    task_type = config.experiment.task_type
    
    adapter_a = TaskAAdapter(chunk_count=config.workload.chunk_count)
    adapter_b = TaskBAdapter(total_steps=config.workload.chunk_count)
    
    while not stop_event.is_set():
        try:
            wait_start = time.time()
            msg = broker.task_queue.get(timeout=0.1)
            wait_end = time.time()
            logger.profiling(trace_id, "queue_based", "queue_lock_wait_ms", (wait_end - wait_start) * 1000, worker_id)
        except queue.Empty:
            continue
            
        task_id = msg.get("task_id")
        logger.dequeued(trace_id, "queue_based", task_id, worker_id, details={"queue_depth": broker.task_queue.qsize()})
        
        try:
            check_crash(config, worker_id, logger, trace_id, "queue_based", task_id)
        except CrashSimulationError:
            # Worker dies completely on crash, chunk is dropped
            break
        
        logger.inference_start(trace_id, "queue_based", task_id, worker_id)
        
        logger.execution_start(trace_id, "queue_based", task_id, worker_id, "mock")
        if latency_sec > 0:
            time.sleep(latency_sec)
            
        context = {"logger": logger, "trace_id": trace_id, "architecture": "queue_based", "worker_id": worker_id}
            
        if task_type == "A":
            chunk = msg.get("payload")
            res = adapter_a.process_chunk(chunk, context=context)
            logger.execution_end(trace_id, "queue_based", task_id, worker_id, "mock", int(latency_sec * 1000))
            broker.result_queue.put({"task_id": task_id, "result": res})
        elif task_type == "B":
            state = msg.get("payload")
            new_state = adapter_b.process_step(state, context=context)
            logger.execution_end(trace_id, "queue_based", task_id, worker_id, "mock", int(latency_sec * 1000))
            if new_state["is_complete"]:
                broker.result_queue.put({"task_id": task_id, "result": new_state})
            else:
                next_task_id = f"{run_id}-step-{new_state['current_step']}"
                logger.dispatch_start(trace_id, "queue_based", next_task_id, worker_id, "queue_put")
                broker.task_queue.put({"task_id": next_task_id, "payload": new_state})
                logger.dispatch_end(trace_id, "queue_based", next_task_id, worker_id, "queue_put")
                logger.queued(trace_id, "queue_based", next_task_id, details={"queue_depth": broker.task_queue.qsize()})

        logger.inference_end(trace_id, "queue_based", task_id, worker_id, config.simulation.mock_inference_latency_ms)
        broker.task_queue.task_done()

def execute(config: GlobalConfig, logger: StructuredLogger, run_id: str, trace_id: str):
    """
    Executes the Queue-based architecture baseline using an in-memory message broker.
    Orchestrator publishes tasks to the queue and waits for results.
    Workers continuously pull from the queue.
    """
    task_type = config.experiment.task_type
    worker_count = config.experiment.worker_count
    
    broker = MessageBroker()
    stop_event = threading.Event()
    
    # Start worker threads
    workers = []
    for i in range(worker_count):
        worker_id = f"queue-worker-{i+1}"
        t = threading.Thread(target=queue_worker_loop, args=(broker, worker_id, config, logger, run_id, trace_id, stop_event))
        t.daemon = True
        t.start()
        workers.append(t)
        
    orchestrator_id = "orchestrator"
    logger.log_event(LogEvent(trace_id=trace_id, architecture="queue_based", task_id="orchestrator-init", event_type=EventType.TASK_RECEIVED, worker_id=orchestrator_id))
    
    # Check if orchestrator crashes (SPOF)
    check_crash(config, orchestrator_id, logger, trace_id, "queue_based", "orchestrator-init")
    
    if task_type == "A":
        adapter = TaskAAdapter(chunk_count=config.workload.chunk_count)
        chunks = adapter.split("dummy_input_data")
        
        for chunk in chunks:
            chunk_task_id = f"{run_id}-{chunk['chunk_id']}"
            logger.dispatch_start(trace_id, "queue_based", chunk_task_id, orchestrator_id, "queue_put")
            broker.task_queue.put({"task_id": chunk_task_id, "payload": chunk})
            logger.dispatch_end(trace_id, "queue_based", chunk_task_id, orchestrator_id, "queue_put")
            logger.queued(trace_id, "queue_based", chunk_task_id, details={"queue_depth": broker.task_queue.qsize()})
            
        results = []
        pending_chunks = {f"{run_id}-{chunk['chunk_id']}": chunk for chunk in chunks}
        
        # Wait for results and retry on timeout
        while pending_chunks:
            # Check if all workers are dead
            if not any(w.is_alive() for w in workers):
                logger.log_event(LogEvent(trace_id=trace_id, architecture="queue_based", task_id="orchestrator-fail", event_type=EventType.TASK_COMPLETED, worker_id=orchestrator_id, details={"status": "failed", "reason": "All workers crashed"}))
                raise CrashSimulationError("All workers crashed")
                
            try:
                res_msg = broker.result_queue.get(timeout=10.0)
                task_id_val = res_msg["task_id"]
                
                if task_id_val in pending_chunks:
                    results.append(res_msg["result"])
                    pending_chunks.pop(task_id_val)
                elif task_id_val.endswith("-retry"):
                    orig_id = task_id_val.replace("-retry", "")
                    if orig_id in pending_chunks:
                        logger.retry_end(trace_id, "queue_based", orig_id)
                        results.append(res_msg["result"])
                        pending_chunks.pop(orig_id)
                
                broker.result_queue.task_done()
            except queue.Empty:
                # Timeout occurred! Re-queue the pending chunks to simulate Dead Letter Queue retry
                for chunk_task_id, chunk in pending_chunks.items():
                    logger.retry_start(trace_id, "queue_based", chunk_task_id)
                    logger.queue_stall(trace_id, "queue_based", chunk_task_id, orchestrator_id, 10000, root_cause="queue_stall")
                    logger.dispatch_start(trace_id, "queue_based", f"{chunk_task_id}-retry", orchestrator_id, "queue_put")
                    broker.task_queue.put({"task_id": f"{chunk_task_id}-retry", "payload": chunk})
                    logger.dispatch_end(trace_id, "queue_based", f"{chunk_task_id}-retry", orchestrator_id, "queue_put")
                    logger.queued(trace_id, "queue_based", f"{chunk_task_id}-retry", details={"queue_depth": broker.task_queue.qsize()})
            
        logger.log_event(LogEvent(trace_id=trace_id, architecture="queue_based", task_id="aggregation", event_type=EventType.AGGREGATION_START, worker_id=orchestrator_id))
        final_result = adapter.aggregate(results)
        logger.log_event(LogEvent(trace_id=trace_id, architecture="queue_based", task_id="aggregation", event_type=EventType.AGGREGATION_END, worker_id=orchestrator_id))
        
    elif task_type == "B":
        adapter = TaskBAdapter(total_steps=config.workload.chunk_count)
        state = adapter.create_initial_state("dummy_query")
        
        step_task_id = f"{run_id}-step-{state['current_step']}"
        logger.dispatch_start(trace_id, "queue_based", step_task_id, orchestrator_id, "queue_put")
        broker.task_queue.put({"task_id": step_task_id, "payload": state})
        logger.dispatch_end(trace_id, "queue_based", step_task_id, orchestrator_id, "queue_put")
        logger.queued(trace_id, "queue_based", step_task_id, details={"queue_depth": broker.task_queue.qsize()})
        
        # Wait for the single final result
        try:
            res_msg = broker.result_queue.get(timeout=30.0)
            final_result = res_msg["result"]
            broker.result_queue.task_done()
        except queue.Empty:
            final_result = None  # Chain failed
        
    else:
        stop_event.set()
        raise ValueError(f"Unknown task_type: {task_type}")

    # Shutdown workers
    stop_event.set()
    for w in workers:
        w.join(timeout=1.0)
