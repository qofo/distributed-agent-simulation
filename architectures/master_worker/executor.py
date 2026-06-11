import time
import concurrent.futures
from core.config import GlobalConfig
from core.logger import StructuredLogger
from workloads.task_a import TaskAAdapter
from workloads.task_b import TaskBAdapter
from core.log_schema import LogEvent, EventType
from core.failure_injection import get_effective_latency, check_crash, CrashSimulationError

def worker_task_a(chunk, adapter, config: GlobalConfig, logger: StructuredLogger, run_id: str, trace_id: str, worker_id: str):
    chunk_task_id = f"{run_id}-{chunk['chunk_id']}"
    latency_sec = get_effective_latency(config, worker_id)

    logger.worker_state(trace_id, "master_worker", worker_id, "busy")
    logger.dequeued(trace_id, "master_worker", chunk_task_id, worker_id)
    
    check_crash(config, worker_id, logger, trace_id, "master_worker", chunk_task_id)
    
    logger.inference_start(trace_id, "master_worker", chunk_task_id, worker_id)
    
    logger.execution_start(trace_id, "master_worker", chunk_task_id, worker_id, "mock")
    if latency_sec > 0:
        logger.worker_state(trace_id, "master_worker", worker_id, "blocked")
        time.sleep(latency_sec)
        logger.worker_state(trace_id, "master_worker", worker_id, "busy")
    
    context = {"logger": logger, "trace_id": trace_id, "architecture": "master_worker", "worker_id": worker_id}
    res = adapter.process_chunk(chunk, context=context)
    logger.execution_end(trace_id, "master_worker", chunk_task_id, worker_id, "mock", int(latency_sec * 1000))
    
    logger.inference_end(trace_id, "master_worker", chunk_task_id, worker_id, config.simulation.mock_inference_latency_ms)
    logger.worker_state(trace_id, "master_worker", worker_id, "idle")
    return res

def worker_task_b(state, adapter, config: GlobalConfig, logger: StructuredLogger, run_id: str, trace_id: str, worker_id: str):
    step_id = state["current_step"]
    step_task_id = f"{run_id}-step-{step_id}"
    latency_sec = get_effective_latency(config, worker_id)

    logger.worker_state(trace_id, "master_worker", worker_id, "busy")
    logger.dequeued(trace_id, "master_worker", step_task_id, worker_id)
    
    check_crash(config, worker_id, logger, trace_id, "master_worker", step_task_id)
    
    logger.inference_start(trace_id, "master_worker", step_task_id, worker_id)
    
    logger.execution_start(trace_id, "master_worker", step_task_id, worker_id, "mock")
    if latency_sec > 0:
        logger.worker_state(trace_id, "master_worker", worker_id, "blocked")
        time.sleep(latency_sec)
        logger.worker_state(trace_id, "master_worker", worker_id, "busy")
        
    context = {"logger": logger, "trace_id": trace_id, "architecture": "master_worker", "worker_id": worker_id}
    new_state = adapter.process_step(state, context=context)
    logger.execution_end(trace_id, "master_worker", step_task_id, worker_id, "mock", int(latency_sec * 1000))
    
    logger.inference_end(trace_id, "master_worker", step_task_id, worker_id, config.simulation.mock_inference_latency_ms)
    logger.worker_state(trace_id, "master_worker", worker_id, "idle")
    return new_state

def execute(config: GlobalConfig, logger: StructuredLogger, run_id: str, trace_id: str):
    """
    Executes the master-worker architecture baseline.
    The Master thread uses a ThreadPoolExecutor to dispatch tasks to Worker threads.
    """
    task_type = config.experiment.task_type
    worker_count = config.experiment.worker_count

    if task_type == "A":
        adapter = TaskAAdapter(chunk_count=config.workload.chunk_count)
        chunks = adapter.split("dummy_input_data")
        
        # Log master overhead start
        master_id = "master-node"
        logger.worker_state(trace_id, "master_worker", master_id, "busy")
        logger.log_event(LogEvent(trace_id=trace_id, architecture="master_worker", task_id="master-dispatch", event_type=EventType.TASK_RECEIVED, worker_id=master_id))
        
        # Check if master crashes (SPOF)
        check_crash(config, master_id, logger, trace_id, "master_worker", "master-dispatch")
        
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = []
            for i, chunk in enumerate(chunks):
                chunk_task_id = f"{run_id}-{chunk['chunk_id']}"
                logger.queued(trace_id, "master_worker", chunk_task_id)
                
                worker_id = f"mw-worker-{i % worker_count + 1}"
                logger.dispatch_start(trace_id, "master_worker", chunk_task_id, master_id, "master_worker_submit")
                futures.append(executor.submit(worker_task_a, chunk, adapter, config, logger, run_id, trace_id, worker_id))
                logger.dispatch_end(trace_id, "master_worker", chunk_task_id, master_id, "master_worker_submit")
            
            logger.worker_state(trace_id, "master_worker", master_id, "blocked")
            for future in concurrent.futures.as_completed(futures):
                try:
                    results.append(future.result())
                except CrashSimulationError as e:
                    raise e  # Fail the whole request if a worker crashes without retry logic
            logger.worker_state(trace_id, "master_worker", master_id, "busy")

        # Aggregation
        agg_start_time = time.time()
        logger.log_event(LogEvent(trace_id=trace_id, architecture="master_worker", task_id="aggregation", event_type=EventType.AGGREGATION_START, worker_id=master_id))
        final_result = adapter.aggregate(results)
        logger.log_event(LogEvent(trace_id=trace_id, architecture="master_worker", task_id="aggregation", event_type=EventType.AGGREGATION_END, worker_id=master_id))
        agg_end_time = time.time()
        logger.profiling(trace_id, "master_worker", "master_aggregation_duration_ms", (agg_end_time - agg_start_time) * 1000, master_id)
        logger.worker_state(trace_id, "master_worker", master_id, "idle")
        
    elif task_type == "B":
        adapter = TaskBAdapter(total_steps=config.workload.chunk_count)
        state = adapter.create_initial_state("dummy_query")
        
        master_id = "master-node"
        logger.worker_state(trace_id, "master_worker", master_id, "busy")
        logger.log_event(LogEvent(trace_id=trace_id, architecture="master_worker", task_id="master-dispatch", event_type=EventType.TASK_RECEIVED, worker_id=master_id))
        
        # Check if master crashes (SPOF)
        check_crash(config, master_id, logger, trace_id, "master_worker", "master-dispatch")
        
        # For chained reasoning, tasks must run sequentially. The master coordinates handoff.
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            step_counter = 0
            while not state["is_complete"]:
                step_task_id = f"{run_id}-step-{state['current_step']}"
                logger.queued(trace_id, "master_worker", step_task_id)
                
                worker_id = f"mw-worker-{(step_counter % worker_count) + 1}"
                logger.dispatch_start(trace_id, "master_worker", step_task_id, master_id, "master_worker_submit")
                future = executor.submit(worker_task_b, state, adapter, config, logger, run_id, trace_id, worker_id)
                logger.dispatch_end(trace_id, "master_worker", step_task_id, master_id, "master_worker_submit")
                
                logger.worker_state(trace_id, "master_worker", master_id, "blocked")
                try:
                    state = future.result()
                except CrashSimulationError as e:
                    raise e  # Fail the request on crash
                logger.worker_state(trace_id, "master_worker", master_id, "busy")
                
                # Master logs handoff overhead optionally, or we consider handoff time as part of queue time.
                if not state["is_complete"]:
                    logger.log_event(LogEvent(trace_id=trace_id, architecture="master_worker", task_id=f"handoff-{state['current_step']}", event_type=EventType.HANDOFF, worker_id=master_id, details={"target_worker": f"mw-worker-{((step_counter + 1) % worker_count) + 1}"}))
                
                step_counter += 1
        logger.worker_state(trace_id, "master_worker", master_id, "idle")

    else:
        raise ValueError(f"Unknown task_type: {task_type}")
