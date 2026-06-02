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

def generate_run_id(config: GlobalConfig) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    short_uuid = str(uuid.uuid4())[:8]
    return f"{timestamp}_{config.experiment.architecture}_{config.experiment.task_type}_{short_uuid}"

def setup_run_directories(run_id: str) -> dict:
    base_dir = Path(__file__).resolve().parent.parent
    
    run_log_dir = base_dir / "logs" / "runs" / run_id
    run_result_dir = base_dir / "results" / "runs" / run_id
    
    run_log_dir.mkdir(parents=True, exist_ok=True)
    run_result_dir.mkdir(parents=True, exist_ok=True)
    
    return {
        "log_dir": run_log_dir,
        "result_dir": run_result_dir
    }

def main():
    parser = argparse.ArgumentParser(description="Distributed Agent Simulation Runner")
    parser.add_argument("--config", type=str, required=True, help="Path to experiment config YAML")
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
            "config": {
                "experiment": config.experiment.__dict__,
                "workload": config.workload.__dict__,
                "simulation": {
                    "mock_inference_latency_ms": config.simulation.mock_inference_latency_ms,
                    "timeout_threshold_ms": config.simulation.timeout_threshold_ms,
                    "retry_policy": config.simulation.retry_policy.__dict__
                },
                "failure_injection": config.failure_injection.__dict__
            }
        }
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
            
        # 5. Initialize Logger for this run
        log_file_path = dirs["log_dir"] / "events.jsonl"
        logger = StructuredLogger(name=f"run_{run_id}", log_file=str(log_file_path))
        
        # Log system start
        trace_id = f"sys-{run_id}"
        logger.task_received(trace_id, config.experiment.architecture, "runner-init", {"run_id": run_id})
        
        print(f"[{datetime.now().isoformat()}] INFO: Starting run {run_id} (Arch: {config.experiment.architecture})")
        
        # 6. Execute architecture logic (Placeholder for now)
        # TODO: Dynamically load architectures based on config.experiment.architecture
        print(f"[{datetime.now().isoformat()}] INFO: Architecture execution will be implemented in future phases.")
        
        # Simulate successful completion
        logger.task_completed(trace_id, config.experiment.architecture, "runner-finish", {"status": "success"})
        
        print(f"[{datetime.now().isoformat()}] INFO: Run {run_id} completed successfully.")
        sys.exit(0)
        
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] ERROR: Experiment run failed.")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
