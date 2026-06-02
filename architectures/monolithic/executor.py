import time
from core.config import GlobalConfig
from core.logger import StructuredLogger
from workloads.task_a import TaskAAdapter
from workloads.task_b import TaskBAdapter

def execute(config: GlobalConfig, logger: StructuredLogger, run_id: str, trace_id: str):
    """
    Executes the monolithic architecture baseline.
    All processing happens sequentially in a single process.
    """
    task_type = config.experiment.task_type
    latency_sec = config.simulation.mock_inference_latency_ms / 1000.0

    if task_type == "A":
        # Map-Reduce
        adapter = TaskAAdapter(chunk_count=config.workload.chunk_count)
        chunks = adapter.split("dummy_input_data")
        
        results = []
        worker_id = "mono-worker-1"
        
        for chunk in chunks:
            chunk_task_id = f"{run_id}-{chunk['chunk_id']}"
            
            # Start inference
            logger.inference_start(trace_id, "monolithic", chunk_task_id, worker_id)
            
            # Simulate work
            if latency_sec > 0:
                time.sleep(latency_sec)
                
            res = adapter.process_chunk(chunk)
            results.append(res)
            
            # End inference
            logger.inference_end(trace_id, "monolithic", chunk_task_id, worker_id, config.simulation.mock_inference_latency_ms)
            
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
        
        while not state["is_complete"]:
            step_id = state["current_step"]
            step_task_id = f"{run_id}-step-{step_id}"
            
            # Start inference
            logger.inference_start(trace_id, "monolithic", step_task_id, worker_id)
            
            # Simulate work
            if latency_sec > 0:
                time.sleep(latency_sec)
                
            state = adapter.process_step(state)
            
            # End inference
            logger.inference_end(trace_id, "monolithic", step_task_id, worker_id, config.simulation.mock_inference_latency_ms)
            
    else:
        raise ValueError(f"Unknown task_type: {task_type}")
