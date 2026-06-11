import os
import subprocess
import json
import yaml
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent

# Use the same parameters as the latest batch run to match existing data
CONFIG_TEMPLATE = {
    "experiment": {
        "name": "",
        "architecture": "",
        "worker_count": 1,
        "task_type": "A"
    },
    "workload": {
        "chunk_count": 64,
        "dataset_path": "./data/dummy.json",
        "total_requests": 10,
        "requests_per_second": 10.0
    },
    "simulation": {
        "mock_inference_latency_ms": 2000,
        "timeout_threshold_ms": 5000,
        "retry_policy": {"enabled": True, "max_retries": 3}
    },
    "failure_injection": {
        "mode": "none",
        "target_worker_id": None,
        "timing_ms": 0,
        "straggler_delay_ms": 0
    }
}

MISSING_MATRIX = [
    {"arch": "monolithic", "task": "A", "workers": 1, "chunks": 64, "latency": 2000},
    {"arch": "master_worker", "task": "A", "workers": 8, "chunks": 64, "latency": 2000},
    {"arch": "swarm", "task": "A", "workers": 2, "chunks": 64, "latency": 2000},
]

def run_missing():
    batch_id = f"missing_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    batch_dir = BASE_DIR / "results" / "batches" / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    
    temp_configs_dir = batch_dir / "configs"
    temp_configs_dir.mkdir(exist_ok=True)
    
    print(f"Starting missing experiments: {batch_id}")
    
    run_log_dirs = []
    
    for params in MISSING_MATRIX:
        arch = params["arch"]
        task = params["task"]
        workers = params["workers"]
        
        # We will run 3 trials for each configuration to match previous data statistical significance
        for trial in range(3):
            name = f"run_missing_{arch}_T{task}_W{workers}_trial{trial}"
            
            cfg = json.loads(json.dumps(CONFIG_TEMPLATE))
            cfg["experiment"]["name"] = name
            cfg["experiment"]["architecture"] = arch
            cfg["experiment"]["task_type"] = task
            cfg["experiment"]["worker_count"] = workers
            cfg["workload"]["chunk_count"] = params["chunks"]
            cfg["simulation"]["mock_inference_latency_ms"] = params["latency"]
            
            cfg_path = temp_configs_dir / f"{name}.yaml"
            with open(cfg_path, "w", encoding="utf-8") as f:
                yaml.dump(cfg, f)
                
            print(f"Executing {name} ...")
            runner_path = BASE_DIR / "runner" / "run_experiment.py"
            result = subprocess.run(
                ["python", str(runner_path), "--config", str(cfg_path)],
                capture_output=True,
                text=True,
                cwd=str(BASE_DIR)
            )
            
            if result.returncode != 0:
                print(f"  -> ERROR: {name} failed.")
                print(result.stderr)
                continue
                
            run_id = None
            for line in result.stdout.split('\n'):
                if "INFO: Starting run " in line:
                    parts = line.split("INFO: Starting run ")[1]
                    run_id = parts.split(" ")[0]
                    break
                    
            if run_id:
                print(f"  -> Success. Run ID: {run_id}")
                run_log_dirs.append(BASE_DIR / "result4" / "runs" / run_id)
            else:
                print(f"  -> Warning: Could not parse run_id for {name}")

    print("\nMissing batch execution complete. Parsing metrics...")
    summary_csv_path = batch_dir / "missing_summary.csv"
    
    parser_path = BASE_DIR / "parser" / "metrics_parser.py"
    
    for log_dir in run_log_dirs:
        subprocess.run(
            ["python", str(parser_path), "--log_dir", str(log_dir), "--output_csv", str(summary_csv_path)],
            capture_output=True,
            cwd=str(BASE_DIR)
        )
        
    print(f"Missing batch summary generated at: {summary_csv_path}")

if __name__ == "__main__":
    run_missing()
