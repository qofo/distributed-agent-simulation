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
        "worker_count": 4,
        "task_type": "A"
    },
    "workload": {
        "chunk_count": 100,
        "dataset_path": "./data/dummy.json",
        "total_requests": 100,
        "requests_per_second": 10.0
    },
    "simulation": {
        "mock_inference_latency_ms": 500,
        "timeout_threshold_ms": 5000,
        "retry_policy": {"enabled": True, "max_retries": 3}
    },
    "failure_injection": {
        "mode": "none",
        "target_worker_id": None,
        "timing_ms": 2000,
        "straggler_delay_ms": 0,
        "combined_mode": False
    }
}

MATRIX = [
    # Baseline for reference
    {"arch": "master_worker", "task": "A", "mode": "none", "target": None},
    {"arch": "queue_based", "task": "A", "mode": "none", "target": None},
    
    # Single Failure: Crash
    {"arch": "master_worker", "task": "A", "mode": "crash", "target": "mw-worker-1"},
    {"arch": "queue_based", "task": "A", "mode": "crash", "target": "queue-worker-1"},
    
    # Single Failure: Straggler
    {"arch": "master_worker", "task": "A", "mode": "straggler", "target": "mw-worker-2", "straggler_delay": 3000},
    {"arch": "queue_based", "task": "A", "mode": "straggler", "target": "queue-worker-2", "straggler_delay": 3000},
    
    # Combined Failure: Crash + Straggler
    {"arch": "master_worker", "task": "A", "mode": "crash_and_straggler", "target": "mw-worker-1", "straggler_target": "mw-worker-2", "straggler_delay": 3000},
    {"arch": "queue_based", "task": "A", "mode": "crash_and_straggler", "target": "queue-worker-1", "straggler_target": "queue-worker-2", "straggler_delay": 3000},
]

def run_failure_batch():
    batch_id = f"phase2c_fail_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    batch_dir = BASE_DIR / "results" / "phase2c" / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    
    temp_configs_dir = batch_dir / "configs"
    temp_configs_dir.mkdir(exist_ok=True)
    
    print(f"Starting Phase 2C Failure Experiment: {batch_id}")
    
    run_log_info = []
    
    for idx, params in enumerate(MATRIX):
        arch = params["arch"]
        task = params["task"]
        mode = params["mode"]
        
        base_name = f"{arch}_T{task}_{mode}"
            
        iterations = 5 # 5 iterations for failure runs
        for i in range(iterations):
            name = f"{base_name}_iter{i}"
            
            cfg = json.loads(json.dumps(CONFIG_TEMPLATE))
            cfg["experiment"]["name"] = name
            cfg["experiment"]["architecture"] = arch
            
            if mode == "none":
                cfg["failure_injection"]["mode"] = "none"
            elif mode == "crash":
                cfg["failure_injection"]["mode"] = "crash"
                cfg["failure_injection"]["target_worker_id"] = params["target"]
            elif mode == "straggler":
                cfg["failure_injection"]["mode"] = "straggler"
                cfg["failure_injection"]["target_worker_id"] = params["target"]
                cfg["failure_injection"]["straggler_delay_ms"] = params["straggler_delay"]
            elif mode == "crash_and_straggler":
                # We need to modify the config or code to support combined mode.
                # Assuming failure_injection logic is updated to handle 'combined_mode'
                cfg["failure_injection"]["mode"] = "crash"
                cfg["failure_injection"]["target_worker_id"] = params["target"]
                cfg["failure_injection"]["combined_mode"] = True
                cfg["failure_injection"]["straggler_target_id"] = params["straggler_target"]
                cfg["failure_injection"]["straggler_delay_ms"] = params["straggler_delay"]
            
            cfg_path = temp_configs_dir / f"{name}.yaml"
            with open(cfg_path, "w", encoding="utf-8") as f:
                yaml.dump(cfg, f)
                
            print(f"[{idx*iterations + i + 1}/{len(MATRIX)*iterations}] Executing {name} ...")
            
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
                log_dir = BASE_DIR / "logs" / run_id
                if not log_dir.exists():
                    log_dir = BASE_DIR / "results" / "runs" / run_id
                run_log_info.append((log_dir, base_name))
                
    print("\nBatch execution complete. Parsing metrics...")
    summary_csv_path = batch_dir / "failure_summary.csv"
    
    parser_path = BASE_DIR / "parser" / "metrics_parser.py"
    
    for log_dir, r_name in run_log_info:
        if log_dir.exists():
            subprocess.run(
                ["python", str(parser_path), "--log_dir", str(log_dir), "--output_csv", str(summary_csv_path), "--run_name", r_name],
                capture_output=True,
                cwd=str(BASE_DIR)
            )
        
    print(f"Phase 2C summary generated at: {summary_csv_path}")

if __name__ == "__main__":
    run_failure_batch()
