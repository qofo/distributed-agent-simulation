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
        "chunk_count": 20,
        "dataset_path": "./data/dummy.json"
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

# Sweep over latency to find where Monolithic (W=1) crosses Queue-Based (W=4)
LATENCIES_MS = [10, 50, 100, 300, 500, 1000, 2000]

def run_sweep():
    batch_id = f"sweep_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    batch_dir = BASE_DIR / "result5" / "sweeps" / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    
    temp_configs_dir = batch_dir / "configs"
    temp_configs_dir.mkdir(exist_ok=True)
    
    print(f"Starting sweep experiment: {batch_id}")
    
    run_log_info = []
    
    for lat in LATENCIES_MS:
        # Run Monolithic
        for arch, workers in [("monolithic", 1), ("queue_based", 4)]:
            name = f"sweep_{arch}_W{workers}_L{lat}"
            
            cfg = json.loads(json.dumps(CONFIG_TEMPLATE))
            cfg["experiment"]["name"] = name
            cfg["experiment"]["architecture"] = arch
            cfg["experiment"]["worker_count"] = workers
            cfg["simulation"]["mock_inference_latency_ms"] = lat
            
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
            
            run_id = None
            for line in result.stdout.split('\n'):
                if "INFO: Starting run " in line:
                    parts = line.split("INFO: Starting run ")[1]
                    run_id = parts.split(" ")[0]
                    break
                    
            if run_id:
                run_log_info.append((BASE_DIR / "result4" / "runs" / run_id, name))
            
    print("\nSweep execution complete. Parsing metrics...")
    summary_csv_path = batch_dir / "summary.csv"
    
    parser_path = BASE_DIR / "parser" / "metrics_parser.py"
    for log_dir, r_name in run_log_info:
        subprocess.run(
            ["python", str(parser_path), "--log_dir", str(log_dir), "--output_csv", str(summary_csv_path), "--run_name", r_name],
            capture_output=True,
            cwd=str(BASE_DIR)
        )
        
        
    print(f"Sweep summary generated at: {summary_csv_path}")
    
    print("\nGenerating sweep report...")
    report_script_path = BASE_DIR / "reports" / "generate_sweep_report.py"
    subprocess.run(
        ["python", str(report_script_path), "--batch_dir", str(batch_dir), "--output_dir", "report5_sweep"],
        cwd=str(BASE_DIR)
    )
    print("Sweep execution and reporting completed.")

if __name__ == "__main__":
    run_sweep()
