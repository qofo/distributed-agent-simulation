import os
import subprocess
import json
import yaml
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_TEMPLATE = {
    "experiment": {
        "name": "",
        "architecture": "",
        "worker_count": 1,
        "task_type": "A"
    },
    "workload": {
        "chunk_count": 10,
        "dataset_path": "./data/dummy.json",
        "total_requests": 10,
        "requests_per_second": 10.0
    },
    "simulation": {
        "mock_inference_latency_ms": 100,
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

MATRIX = []

# 1. Baseline Variability (No Failure)
MATRIX.append({
    "arch": "queue_based", "task": "A", "workers": 8, "chunks": 200, "latency": 500, "iterations": 20, "is_baseline": True
})

# 2. Experimental Validity Matrix
architectures = ["monolithic", "master_worker", "queue_based", "swarm"]
workers_list = [1, 2, 4, 8, 16]
requests_list = [50, 100, 200, 500]

for arch in architectures:
    for workers in workers_list:
        if arch == "monolithic" and workers > 1:
            continue
        for reqs in requests_list:
            MATRIX.append({
                "arch": arch, "task": "A", "workers": workers, "chunks": reqs, "latency": 500, "iterations": 10
            })

def run_batch():
    batch_id = f"phase2a_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    batch_dir = BASE_DIR / "results" / "phase2a" / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    
    temp_configs_dir = batch_dir / "configs"
    temp_configs_dir.mkdir(exist_ok=True)
    
    print(f"Starting Phase 2A Batch Experiment: {batch_id}")
    total_runs = sum(item.get("iterations", 10) for item in MATRIX)
    print(f"Total configurations: {len(MATRIX)}, Total runs: {total_runs}")
    
    run_log_info = []
    
    current_run = 0
    for params in MATRIX:
        arch = params["arch"]
        task = params["task"]
        workers = params["workers"]
        chunks = params["chunks"]
        
        base_name = f"{arch}_T{task}_W{workers}_R{chunks}"
        if params.get("is_baseline"):
            base_name = f"baseline_{base_name}"
            
        iterations = params.get("iterations", 10)
        for i in range(iterations):
            current_run += 1
            name = f"{base_name}_iter{i}"
            
            cfg = json.loads(json.dumps(CONFIG_TEMPLATE))
            cfg["experiment"]["name"] = name
            cfg["experiment"]["architecture"] = arch
            cfg["experiment"]["task_type"] = task
            cfg["experiment"]["worker_count"] = workers
            cfg["workload"]["chunk_count"] = chunks
            cfg["simulation"]["mock_inference_latency_ms"] = params["latency"]
            
            cfg_path = temp_configs_dir / f"{name}.yaml"
            with open(cfg_path, "w", encoding="utf-8") as f:
                yaml.dump(cfg, f)
                
            print(f"[{current_run}/{total_runs}] Executing {name} ...")
            
            runner_path = BASE_DIR / "runner" / "run_experiment.py"
            result = subprocess.run(
                ["python", str(runner_path), "--config", str(cfg_path)],
                capture_output=True,
                text=True,
                cwd=str(BASE_DIR)
            )
            
            if result.returncode != 0:
                print(f"  -> ERROR: {name} failed.")
                continue
                
            run_id = None
            for line in result.stdout.split('\n'):
                if "INFO: Starting run " in line:
                    parts = line.split("INFO: Starting run ")[1]
                    run_id = parts.split(" ")[0]
                    break
                    
            if run_id:
                # Add to run_log_info for parsing
                log_dir = BASE_DIR / "logs" / run_id
                if not log_dir.exists():
                    log_dir = BASE_DIR / "results" / "runs" / run_id
                run_log_info.append((log_dir, base_name))
            else:
                print(f"  -> Warning: Could not parse run_id for {name}")
                
    # Parse all metrics and generate summary CSV
    print("\nBatch execution complete. Parsing metrics...")
    summary_csv_path = batch_dir / "summary.csv"
    
    parser_path = BASE_DIR / "parser" / "metrics_parser.py"
    
    for log_dir, r_name in run_log_info:
        if log_dir.exists():
            subprocess.run(
                ["python", str(parser_path), "--log_dir", str(log_dir), "--output_csv", str(summary_csv_path), "--run_name", r_name],
                capture_output=True,
                cwd=str(BASE_DIR)
            )
        
    print(f"Phase 2A summary generated at: {summary_csv_path}")

    # Call dataset_builder.py to build the final statistical dataset (Bootstrap CI)
    dataset_builder_path = BASE_DIR / "analyzer" / "dataset_builder.py"
    if dataset_builder_path.exists():
        print("Running dataset builder...")
        subprocess.run(["python", str(dataset_builder_path), "--input_csv", str(summary_csv_path), "--output_csv", str(batch_dir / "phase2a_benchmark_dataset.csv")], cwd=str(BASE_DIR))

if __name__ == "__main__":
    run_batch()
