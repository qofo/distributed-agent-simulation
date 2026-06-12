import os
import subprocess
import yaml
from pathlib import Path

ARCHITECTURES = ["monolithic", "master_worker", "queue_based", "swarm"]
TASK_TYPES = ["A", "B"]
FAILURE_MODES = [
    {"name": "baseline", "mode": "none", "target": "none", "delay": 0},
    {"name": "crash", "mode": "crash", "target": "worker-2", "delay": 0},
    {"name": "straggler", "mode": "straggler", "target": "worker-2", "delay": 500}
]
RUNS = 3

def create_temp_config(arch, task_type, failure):
    # Mapping arch to worker prefix for target
    target_worker = None
    if failure["mode"] != "none":
        if arch == "monolithic":
            target_worker = "monolithic-1" # Only 1 worker
        elif arch == "master_worker":
            target_worker = "worker-2"
        elif arch == "queue_based":
            target_worker = "queue-worker-2"
        elif arch == "swarm":
            target_worker = "swarm-agent-2"

    config_data = {
        "experiment": {
            "name": f"full_{arch}_{task_type}_{failure['name']}",
            "architecture": arch,
            "task_type": task_type,
            "worker_count": 4 if arch != "monolithic" else 1
        },
        "simulation": {
            "mock_inference_latency_ms": 200,
            "timeout_threshold_ms": 5000,
            "retry_policy": {
                "enabled": True,
                "max_retries": 3
            }
        },
        "workload": {
            "total_requests": 2,
            "requests_per_second": 10.0,
            "chunk_count": 64
        },
        "failure_injection": {
            "mode": failure["mode"],
            "target_worker_id": target_worker,
            "timing_ms": 2000, # crash/delay after 2 seconds roughly
            "straggler_delay_ms": failure["delay"]
        }
    }
    
    os.makedirs("configs/temp_runs", exist_ok=True)
    cfg_path = f"configs/temp_runs/auto_{arch}_{task_type}_{failure['name']}.yaml"
    with open(cfg_path, "w") as f:
        yaml.dump(config_data, f)
    return cfg_path

def main():
    total_runs = len(ARCHITECTURES) * len(TASK_TYPES) * len(FAILURE_MODES) * RUNS
    current_run = 0

    print(f"Starting {total_runs} experiments...")
    
    for arch in ARCHITECTURES:
        for task_type in TASK_TYPES:
            for failure in FAILURE_MODES:
                cfg_path = create_temp_config(arch, task_type, failure)
                for i in range(RUNS):
                    current_run += 1
                    print(f"[{current_run}/{total_runs}] Running {arch} Task {task_type} ({failure['name']}) - Run {i+1}/{RUNS}...")
                    
                    cmd = ["python", "runner/run_experiment.py", "--config", cfg_path]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    print("All experiments completed successfully.")

if __name__ == "__main__":
    main()
