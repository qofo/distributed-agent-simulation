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
            msg = broker.task_queue.get(timeout=0.1)
        except queue.Empty:
            continue
            
        task_id = msg.get("task_id")
        logger.dequeued(trace_id, "queue_based", task_id, worker_id)
        
        try:
            check_crash(config, worker_id, logger, trace_id, "queue_based", task_id)
        except CrashSimulationError:
            broker.task_queue.task_done()
            continue
        
        logger.inference_start(trace_id, "queue_based", task_id, worker_id)
        
        if latency_sec > 0:
            time.sleep(latency_sec)
            
        if task_type == "A":
            chunk = msg.get("payload")
            res = adapter_a.process_chunk(chunk)
            broker.result_queue.put({"task_id": task_id, "result": res})
        elif task_type == "B":
            state = msg.get("payload")
            new_state = adapter_b.process_step(state)
            if new_state["is_complete"]:
                broker.result_queue.put({"task_id": task_id, "result": new_state})
            else:
                next_task_id = f"{run_id}-step-{new_state['current_step']}"
                broker.task_queue.put({"task_id": next_task_id, "payload": new_state})
                logger.queued(trace_id, "queue_based", next_task_id)

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
    
    if task_type == "A":
        adapter = TaskAAdapter(chunk_count=config.workload.chunk_count)
        chunks = adapter.split("dummy_input_data")
        
        for chunk in chunks:
            chunk_task_id = f"{run_id}-{chunk['chunk_id']}"
            broker.task_queue.put({"task_id": chunk_task_id, "payload": chunk})
            logger.queued(trace_id, "queue_based", chunk_task_id)
            
        results = []
        # Wait for results
        for _ in chunks:
            try:
                res_msg = broker.result_queue.get(timeout=2.0)
                results.append(res_msg["result"])
                broker.result_queue.task_done()
            except queue.Empty:
                pass  # Crashed chunk
            
        logger.log_event(LogEvent(trace_id=trace_id, architecture="queue_based", task_id="aggregation", event_type=EventType.AGGREGATION_START, worker_id=orchestrator_id))
        final_result = adapter.aggregate(results)
        logger.log_event(LogEvent(trace_id=trace_id, architecture="queue_based", task_id="aggregation", event_type=EventType.AGGREGATION_END, worker_id=orchestrator_id))
        
    elif task_type == "B":
        adapter = TaskBAdapter(total_steps=config.workload.chunk_count)
        state = adapter.create_initial_state("dummy_query")
        
        step_task_id = f"{run_id}-step-{state['current_step']}"
        broker.task_queue.put({"task_id": step_task_id, "payload": state})
        logger.queued(trace_id, "queue_based", step_task_id)
        
        # Wait for the single final result
        try:
            res_msg = broker.result_queue.get(timeout=2.0)
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
