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
        "chunk_count": 4, # Smaller chunk count for real test
        "dataset_path": "./data/dummy",
        "total_requests": 2, # Small number of requests to save API Quota
        "requests_per_second": 2.0
    },
    "simulation": {
        "mock_inference_latency_ms": 0,
        "timeout_threshold_ms": 30000,
        "retry_policy": {"enabled": True, "max_retries": 3}
    },
    "failure_injection": {
        "mode": "none",
        "target_worker_id": None,
        "timing_ms": 0,
        "straggler_delay_ms": 0
    }
}

MATRIX = [
    # Task A (Map-Reduce)
    {"arch": "monolithic", "task": "A", "workers": 1, "chunks": 4},
    
    # Task B (Multi-hop QA)
    {"arch": "monolithic", "task": "B", "workers": 1, "chunks": 4},
]

def run_batch():
    batch_id = f"real_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    batch_dir = BASE_DIR / "result4" / "batches" / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    
    temp_configs_dir = batch_dir / "configs"
    temp_configs_dir.mkdir(exist_ok=True)
    
    print(f"Starting REAL API batch experiment: {batch_id}")
    print(f"Total configurations to run: {len(MATRIX)}")
    
    run_log_info = []
    
    for idx, params in enumerate(MATRIX):
        arch = params["arch"]
        task = params["task"]
        workers = params["workers"]
        
        base_name = f"run_{idx:02d}_{arch}_T{task}_W{workers}"
        if "straggler_target" in params:
            base_name += "_straggler"
        elif "crash_target" in params:
            base_name += "_crash"
            
        iterations = 2 # Reduced iterations to save quota
        for i in range(iterations):
            name = f"{base_name}_iter{i}"
            
            # Build Config
            cfg = json.loads(json.dumps(CONFIG_TEMPLATE))  # Deep copy
            cfg["experiment"]["name"] = name
            cfg["experiment"]["architecture"] = arch
            cfg["experiment"]["task_type"] = task
            cfg["experiment"]["worker_count"] = workers
            cfg["workload"]["chunk_count"] = params["chunks"]
            
            if "straggler_target" in params:
                cfg["failure_injection"]["mode"] = "straggler"
                cfg["failure_injection"]["target_worker_id"] = params["straggler_target"]
                cfg["failure_injection"]["straggler_delay_ms"] = params.get("straggler_delay", 500)
            elif "crash_target" in params:
                cfg["failure_injection"]["mode"] = "crash"
                cfg["failure_injection"]["target_worker_id"] = params["crash_target"]
            
            cfg_path = temp_configs_dir / f"{name}.yaml"
            with open(cfg_path, "w", encoding="utf-8") as f:
                yaml.dump(cfg, f)
                
            print(f"[{idx+1}/{len(MATRIX)} - Iter {i+1}/{iterations}] Executing {name} ...")
            
            # Run subprocess
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
                run_log_info.append((BASE_DIR / "result4" / "runs" / run_id, base_name))
            else:
                print(f"  -> Warning: Could not parse run_id for {name}")
            
    print("\nBatch execution complete. Parsing metrics...")
    summary_csv_path = batch_dir / "summary.csv"
    
    parser_path = BASE_DIR / "parser" / "metrics_parser.py"
    
    for log_dir, r_name in run_log_info:
        subprocess.run(
            ["python", str(parser_path), "--log_dir", str(log_dir), "--output_csv", str(summary_csv_path), "--run_name", r_name],
            capture_output=True,
            cwd=str(BASE_DIR)
        )
        
    print(f"Batch summary generated at: {summary_csv_path}")
    
    print("\nGenerating report...")
    report_script_path = BASE_DIR / "reports" / "generate_summary.py"
    subprocess.run(
        ["python", str(report_script_path), "--batch_dir", str(batch_dir), "--output_dir", "report_real_api"],
        cwd=str(BASE_DIR)
    )
    print("Batch execution and reporting completed.")

if __name__ == "__main__":
    run_batch()
