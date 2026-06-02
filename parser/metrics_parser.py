import argparse
import json
import csv
import statistics
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any

def parse_time(time_str: str) -> datetime:
    return datetime.fromisoformat(time_str.replace("Z", "+00:00"))

def compute_metrics(log_file: Path, run_name: str) -> Dict[str, Any]:
    events = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    if not events:
        return {}

    # Sort events by timestamp just in case
    events.sort(key=lambda x: parse_time(x["timestamp"]))

    start_time = parse_time(events[0]["timestamp"])
    end_time = parse_time(events[-1]["timestamp"])
    total_duration_sec = (end_time - start_time).total_seconds()

    # Trackers
    request_start_times = {}
    request_latencies = []
    
    queue_start_times = {}
    queue_wait_times = []
    
    completed_requests = 0
    failed_requests = 0
    retries = 0
    timeouts = 0
    crashes = 0
    
    architecture = events[0].get("architecture", "unknown")

    for event in events:
        trace_id = event.get("trace_id")
        task_id = event.get("task_id")
        evt_type = event.get("event_type")
        timestamp = parse_time(event.get("timestamp"))
        
        uniq_key = f"{trace_id}:{task_id}"

        if evt_type == "TASK_RECEIVED":
            request_start_times[trace_id] = timestamp
        elif evt_type == "TASK_COMPLETED":
            if trace_id in request_start_times:
                latency = (timestamp - request_start_times[trace_id]).total_seconds()
                request_latencies.append(latency)
                completed_requests += 1
        elif evt_type == "QUEUED":
            queue_start_times[uniq_key] = timestamp
        elif evt_type == "DEQUEUED":
            if uniq_key in queue_start_times:
                wait_time = (timestamp - queue_start_times[uniq_key]).total_seconds()
                queue_wait_times.append(wait_time)
        elif evt_type == "RETRY":
            retries += 1
        elif evt_type == "TIMEOUT":
            timeouts += 1
        elif evt_type == "CRASH":
            crashes += 1

    # Calculations
    p50_latency = statistics.median(request_latencies) if request_latencies else 0.0
    p95_latency = statistics.quantiles(request_latencies, n=100)[94] if len(request_latencies) > 1 else (request_latencies[0] if request_latencies else 0.0)
    p99_latency = statistics.quantiles(request_latencies, n=100)[98] if len(request_latencies) > 1 else (request_latencies[0] if request_latencies else 0.0)
    
    avg_queue_wait = statistics.mean(queue_wait_times) if queue_wait_times else 0.0
    throughput = (completed_requests / total_duration_sec) if total_duration_sec > 0 else 0.0

    return {
        "run_name": run_name,
        "architecture": architecture,
        "total_requests": len(request_start_times),
        "completed_requests": completed_requests,
        "total_duration_sec": total_duration_sec,
        "throughput_req_per_sec": throughput,
        "p50_latency_sec": p50_latency,
        "p95_latency_sec": p95_latency,
        "p99_latency_sec": p99_latency,
        "avg_queue_wait_sec": avg_queue_wait,
        "retries": retries,
        "timeouts": timeouts,
        "crashes": crashes
    }

def write_csv_summary(metrics: Dict[str, Any], output_path: Path):
    if not metrics:
        return
        
    headers = list(metrics.keys())
    file_exists = output_path.exists()
    
    with open(output_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists:
            writer.writeheader()
        writer.writerow(metrics)

def main():
    parser = argparse.ArgumentParser(description="Distributed Agent Simulation Metrics Parser")
    parser.add_argument("--log_dir", type=str, required=True, help="Path to the directory containing events.jsonl")
    parser.add_argument("--output_csv", type=str, default="results/summary_metrics.csv", help="Path to output CSV")
    parser.add_argument("--run_name", type=str, default="unknown", help="Name of the run")
    args = parser.parse_args()

    log_path = Path(args.log_dir) / "events.jsonl"
    if not log_path.exists():
        print(f"Error: Log file not found at {log_path}")
        sys.exit(1)

    print(f"Parsing {log_path}...")
    metrics = compute_metrics(log_path, args.run_name)
    
    if not metrics:
        print("No valid events found to parse.")
        sys.exit(0)
        
    out_path = Path(args.output_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    write_csv_summary(metrics, out_path)
    print(f"Metrics successfully parsed and written to {out_path}")
    print(json.dumps(metrics, indent=2))

if __name__ == "__main__":
    main()
