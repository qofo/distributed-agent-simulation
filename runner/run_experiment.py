import argparse
import sys
import json
import traceback
from datetime import datetime
from pathlib import Path
import uuid

# Adjust import path if running from root
sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.config import load_config, GlobalConfig
from core.logger import StructuredLogger, EventType
import asyncio

def generate_run_id(config: GlobalConfig) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]
    return f"{timestamp}_{config.experiment.architecture}_{config.experiment.task_type}_{short_uuid}"

def setup_run_directories(run_id: str) -> dict:
    base_dir = Path(__file__).resolve().parent.parent
    run_log_dir = base_dir / "result4" / "runs" / run_id
    run_result_dir = base_dir / "result4" / "runs" / run_id
    
    run_log_dir.mkdir(parents=True, exist_ok=True)
    run_result_dir.mkdir(parents=True, exist_ok=True)
    
    return {
        "log_dir": run_log_dir,
        "result_dir": run_result_dir
    }

async def run_single_request(run_func, config: GlobalConfig, logger: StructuredLogger, run_id: str, req_index: int):
    trace_id = f"sys-{run_id}-req-{req_index}"
    logger.task_received(trace_id, config.experiment.architecture, "request-init", {"req_index": req_index})
    
    try:
        # Execute the architecture block synchronously in a thread
        await asyncio.to_thread(run_func, config, logger, run_id, trace_id)
        logger.task_completed(trace_id, config.experiment.architecture, "request-finish", {"status": "success"})
    except Exception as e:
        logger.task_completed(trace_id, config.experiment.architecture, "request-finish", {"status": "failed", "reason": str(e)})

async def run_single_request_with_sem(sem, run_func, config, logger, run_id, i):
    async with sem:
        await run_single_request(run_func, config, logger, run_id, i)

async def execute_all_requests(run_func, config: GlobalConfig, logger: StructuredLogger, run_id: str):
    total_requests = config.workload.total_requests
    rps = config.workload.requests_per_second
    sleep_interval = 1.0 / rps if rps > 0 else 0
    
    concurrency = getattr(config.workload, "max_concurrent_requests", 100)
    sem = asyncio.Semaphore(concurrency)
    tasks = []
    for i in range(total_requests):
        tasks.append(asyncio.create_task(run_single_request_with_sem(sem, run_func, config, logger, run_id, i)))
        if sleep_interval > 0 and i < total_requests - 1:
            await asyncio.sleep(sleep_interval)
            
    await asyncio.gather(*tasks)

import subprocess

def get_git_commit():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    except Exception:
        return "unknown"

def main():
    parser = argparse.ArgumentParser(description="Distributed Agent Simulation Runner")
    parser.add_argument("--config", type=str, required=True, help="Path to experiment config YAML")
    parser.add_argument(
        "--logger-mode",
        choices=["normal", "disabled", "null"],
        default="normal",
        help=(
            "Logging mode for overhead measurement: "
            "normal=full logging (default), "
            "disabled=I/O blocked (call overhead measured), "
            "null=NullLogger no-op (zero logging cost)"
        )
    )
    args = parser.parse_args()



    try:
        # 1. Load config
        config = load_config(args.config)
        
        # 2. Create unique run ID
        run_id = generate_run_id(config)
        
        # 3. Setup directories
        dirs = setup_run_directories(run_id)
        
        # 4. Save metadata
        metadata_path = dirs["result_dir"] / "metadata.json"
        metadata = {
            "run_id": run_id,
            "start_time": datetime.now().isoformat(),
            "experiment": {
                "task_type": config.experiment.task_type,
                "worker_count": config.experiment.worker_count,
                "git_commit": get_git_commit(),
                "experiment_version": "v1.0.0"
            },
            "simulation": {
                "mock_inference_latency_ms": config.simulation.mock_inference_latency_ms,
                "timeout_threshold_ms": config.simulation.timeout_threshold_ms,
                "retry_policy": config.simulation.retry_policy.__dict__
            },
            "failure_injection": {
                "mode": config.failure_injection.mode,
                "target_worker_id": config.failure_injection.target_worker_id,
                "straggler_delay_ms": config.failure_injection.straggler_delay_ms
            }
        }
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
            
        # 5. Initialize Logger for this run
        log_file_path = dirs["log_dir"] / "events.jsonl"
        logger_mode = args.logger_mode

        if logger_mode == "null":
            from core.null_logger import NullLogger
            logger = NullLogger()
            print(f"[{datetime.now().isoformat()}] INFO: Logger mode = null (NullLogger, no events recorded)")
        elif logger_mode == "disabled":
            logger = StructuredLogger(name=f"run_{run_id}", log_file=str(log_file_path), disabled=True)
            print(f"[{datetime.now().isoformat()}] INFO: Logger mode = disabled (I/O blocked, call overhead measured)")
        else:
            logger = StructuredLogger(name=f"run_{run_id}", log_file=str(log_file_path))

        # Log system start
        trace_id = f"sys-{run_id}"

        logger.run_metadata(trace_id, config.experiment.architecture, metadata)
        
        print(f"[{datetime.now().isoformat()}] INFO: Starting run {run_id} (Arch: {config.experiment.architecture}, Requests: {config.workload.total_requests})")
        
        # 6. Randomize crash target if needed
        if config.failure_injection.mode == "crash" and config.failure_injection.target_worker_id == "random":
            import random
            targets = []
            if config.experiment.architecture == "master_worker":
                targets = ["master-node"] + [f"mw-worker-{i+1}" for i in range(config.experiment.worker_count)]
            elif config.experiment.architecture == "queue_based":
                targets = ["orchestrator"] + [f"queue-worker-{i+1}" for i in range(config.experiment.worker_count)]
            
            if targets:
                config.failure_injection.target_worker_id = random.choice(targets)
                print(f"[{datetime.now().isoformat()}] INFO: Random crash target selected: {config.failure_injection.target_worker_id}")
        
        # 7. Execute architecture logic
        run_func = None
        if config.experiment.architecture == "monolithic":
            from architectures.monolithic.executor import execute as run_monolithic
            run_func = run_monolithic
        elif config.experiment.architecture == "master_worker":
            from architectures.master_worker.executor import execute as run_master_worker
            run_func = run_master_worker
        elif config.experiment.architecture == "queue_based":
            from architectures.queue_based.executor import execute as run_queue_based
            run_func = run_queue_based
        elif config.experiment.architecture == "swarm":
            from architectures.swarm.executor import execute as run_swarm
            run_func = run_swarm
        else:
            print(f"[{datetime.now().isoformat()}] INFO: Architecture '{config.experiment.architecture}' execution is not implemented yet.")
            sys.exit(1)
            
        print(f"[{datetime.now().isoformat()}] INFO: Running {config.experiment.architecture} Architecture...")
        asyncio.run(execute_all_requests(run_func, config, logger, run_id))
        
        print(f"[{datetime.now().isoformat()}] INFO: Run {run_id} completed successfully.")
        sys.exit(0)
        
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] ERROR: Experiment run failed.")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
