import os
import subprocess
import json
import yaml
from pathlib import Path
from datetime import datetime
import time

BASE_DIR = Path(__file__).resolve().parent

CONFIG_TEMPLATE = {
    "experiment": {
        "name": "",
        "architecture": "",
        "worker_count": 1,
        "task_type": "B"
    },
    "workload": {
        "chunk_count": 10,
        "dataset_path": "./data/dummy.json",
        "total_requests": 3,
        "requests_per_second": 5.0
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

matrix = [
    {"arch": "monolithic", "w": 1},
]
for arch in ["master_worker", "queue_based", "swarm"]:
    for w in [4, 16, 32]:
        matrix.append({"arch": arch, "w": w})

batch_id = f"task_b_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
batch_dir = BASE_DIR / "results" / "batches" / batch_id
batch_dir.mkdir(parents=True, exist_ok=True)
configs_dir = batch_dir / "configs"
configs_dir.mkdir(exist_ok=True)

log_dirs = []
for params in matrix:
    name = f"run_{params['arch']}_W{params['w']}"
    cfg = json.loads(json.dumps(CONFIG_TEMPLATE))
    cfg["experiment"]["name"] = name
    cfg["experiment"]["architecture"] = params["arch"]
    cfg["experiment"]["worker_count"] = params["w"]
    
    cfg_path = configs_dir / f"{name}.yaml"
    with open(cfg_path, "w", encoding='utf-8') as f: 
        yaml.dump(cfg, f)
    
    runner = BASE_DIR / "runner" / "run_experiment.py"
    res = subprocess.run(["python", str(runner), "--config", str(cfg_path)], capture_output=True, text=True, cwd=str(BASE_DIR))
    
    run_id = None
    for line in res.stdout.split('\n'):
        if "INFO: Starting run " in line:
            run_id = line.split("INFO: Starting run ")[1].split(" ")[0]
            break
            
    if run_id:
        print(f"Success {name}")
        log_dirs.append(run_id)
    else:
        print(f"Failed {name}:\n{res.stderr}\n{res.stdout}")

time.sleep(1)

out_csv = batch_dir / "summary.csv"
parser = BASE_DIR / "parser" / "metrics_parser.py"

for rid in log_dirs:
    for base_res in ["logs", "results", "result4", "result5"]:
        ld = BASE_DIR / base_res / "runs" / rid
        if ld.exists():
            subprocess.run(["python", str(parser), "--log_dir", str(ld), "--output_csv", str(out_csv)], cwd=str(BASE_DIR))
            break

print(f"Generated {out_csv}")
