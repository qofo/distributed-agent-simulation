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
        "architecture": "monolithic",
        "worker_count": 1,
        "task_type": "A"
    },
    "workload": {
        "chunk_count": 20,
        "dataset_path": "./data/dummy.json",
        "total_requests": 1,
        "requests_per_second": 50.0,
        "max_concurrent_requests": 1
    },
    "simulation": {
        "mock_inference_latency_ms": 10,
        "timeout_threshold_ms": 1000,
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
    {"arch": "monolithic", "task": "A", "instances": 1},
    {"arch": "monolithic", "task": "A", "instances": 2},
    {"arch": "monolithic", "task": "A", "instances": 4},
    {"arch": "monolithic", "task": "A", "instances": 8},
    {"arch": "monolithic", "task": "A", "instances": 16},
    {"arch": "monolithic", "task": "A", "instances": 32},
]

def run_batch():
    batch_id = f"mono_scale_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    batch_dir = BASE_DIR / "result5" / "mono_scale" / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    
    temp_configs_dir = batch_dir / "configs"
    temp_configs_dir.mkdir(exist_ok=True)
    
    print(f"Starting Monolithic Scaling experiment: {batch_id}")
    
    run_log_info = []
    
    for idx, params in enumerate(MATRIX):
        arch = params["arch"]
        task = params["task"]
        instances = params["instances"]
        
        base_name = f"mono_scale_{idx:02d}_{arch}_T{task}_W{instances}"
            
        iterations = 1
        for i in range(iterations):
            name = f"{base_name}_iter{i}"
            
            cfg = json.loads(json.dumps(CONFIG_TEMPLATE))
            cfg["experiment"]["name"] = name
            cfg["experiment"]["architecture"] = arch
            cfg["experiment"]["task_type"] = task
            cfg["experiment"]["worker_count"] = 1 # Each monolithic instance is single-threaded
            cfg["workload"]["total_requests"] = instances # W requests total
            cfg["workload"]["max_concurrent_requests"] = instances # Processed by W instances concurrently
            
            cfg_path = temp_configs_dir / f"{name}.yaml"
            with open(cfg_path, "w", encoding="utf-8") as f:
                yaml.dump(cfg, f)
                
            print(f"[{idx+1}/{len(MATRIX)} - Iter {i+1}/{iterations}] Executing {name} ...")
            
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
            
    print("\nScaling execution complete. Parsing metrics...")
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
        ["python", str(report_script_path), "--batch_dir", str(batch_dir), "--output_dir", "report5_mono_scale"],
        cwd=str(BASE_DIR)
    )
    print("Monolithic scaling execution and reporting completed.")

if __name__ == "__main__":
    run_batch()
