import time
from core.config import GlobalConfig
from core.logger import StructuredLogger
from workloads.task_a import TaskAAdapter
from workloads.task_b import TaskBAdapter
from core.failure_injection import get_effective_latency, check_crash

def execute(config: GlobalConfig, logger: StructuredLogger, run_id: str, trace_id: str):
    """
    Executes the monolithic architecture baseline.
    All processing happens sequentially in a single process.
    """
    task_type = config.experiment.task_type

    if task_type == "A":
        # Map-Reduce
        adapter = TaskAAdapter(chunk_count=config.workload.chunk_count)
        chunks = adapter.split("dummy_input_data")
        
        results = []
        worker_id = "mono-worker-1"
        latency_sec = get_effective_latency(config, worker_id)
        
        for chunk in chunks:
            chunk_task_id = f"{run_id}-{chunk['chunk_id']}"
            
            try:
                # Crash check
                check_crash(config, worker_id, logger, trace_id, "monolithic", chunk_task_id)
                
                # Start inference
                logger.inference_start(trace_id, "monolithic", chunk_task_id, worker_id)
                
                # Simulate work
                if latency_sec > 0:
                    time.sleep(latency_sec)
                    
                context = {"logger": logger, "trace_id": trace_id, "architecture": "monolithic", "worker_id": worker_id}
                res = adapter.process_chunk(chunk, context=context)
                results.append(res)
                
                # End inference
                logger.inference_end(trace_id, "monolithic", chunk_task_id, worker_id, config.simulation.mock_inference_latency_ms)
            except CrashSimulationError:
                continue
            
        # Aggregation
        # Using correct manual event logging for aggregation since we don't have helper
        from core.log_schema import LogEvent, EventType
        logger.log_event(LogEvent(trace_id=trace_id, architecture="monolithic", task_id="aggregation", event_type=EventType.AGGREGATION_START, worker_id=worker_id))
        
        final_result = adapter.aggregate(results)
        
        logger.log_event(LogEvent(trace_id=trace_id, architecture="monolithic", task_id="aggregation", event_type=EventType.AGGREGATION_END, worker_id=worker_id))
        
    elif task_type == "B":
        # Multi-Hop QA
        adapter = TaskBAdapter(total_steps=config.workload.chunk_count)
        state = adapter.create_initial_state("dummy_query")
        worker_id = "mono-worker-1"
        latency_sec = get_effective_latency(config, worker_id)
        
        while not state["is_complete"]:
            step_id = state["current_step"]
            step_task_id = f"{run_id}-step-{step_id}"
            
            try:
                # Crash check
                check_crash(config, worker_id, logger, trace_id, "monolithic", step_task_id)
                
                # Start inference
                logger.inference_start(trace_id, "monolithic", step_task_id, worker_id)
                
                # Simulate work
                if latency_sec > 0:
                    time.sleep(latency_sec)
                    
                context = {"logger": logger, "trace_id": trace_id, "architecture": "monolithic", "worker_id": worker_id}
                state = adapter.process_step(state, context=context)
                
                # End inference
                logger.inference_end(trace_id, "monolithic", step_task_id, worker_id, config.simulation.mock_inference_latency_ms)
            except CrashSimulationError:
                break
            
    else:
        raise ValueError(f"Unknown task_type: {task_type}")
