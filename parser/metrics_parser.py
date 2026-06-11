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
    
    dispatch_start_times = {}
    dispatch_times_by_type = defaultdict(list)
    
    execution_start_times = {}
    execution_times = []
    
    aggregation_start_times = {}
    aggregation_times = []
    
    retry_start_times = {}
    retry_times = []
    
    completed_requests = 0
    
    # New Coordination Cost trackers
    queue_ops = 0
    handoffs = 0
    aggregations = 0
    queue_depth_sum = 0
    queue_depth_count = 0
    queue_depths = []
    
    # New Failure trackers
    worker_crashes = 0
    queue_stalls = 0
    retry_attempts = 0
    timeouts_hit = 0
    failure_root_causes = defaultdict(int)
    
    retries = 0
    timeouts = 0
    crashes = 0
    api_429_errors = 0
    
    profiling_data = {}
    active_workers = defaultdict(int)
    max_active_workers = 0
    
    architecture = events[0].get("architecture", "unknown")
    run_metadata = {}

    for event in events:
        trace_id = event.get("trace_id")
        task_id = event.get("task_id")
        evt_type = event.get("event_type")
        timestamp = parse_time(event.get("timestamp"))
        
        uniq_key = f"{trace_id}:{task_id}"

        if evt_type == "RUN_METADATA":
            run_metadata = event.get("details", {})
        elif evt_type == "TASK_RECEIVED":
            request_start_times[trace_id] = timestamp
        elif evt_type == "TASK_COMPLETED":
            if trace_id in request_start_times:
                latency = (timestamp - request_start_times[trace_id]).total_seconds()
                request_latencies.append(latency)
                completed_requests += 1
        elif evt_type == "DISPATCH_START":
            dispatch_type = event.get("details", {}).get("dispatch_type", "unknown")
            dispatch_start_times[uniq_key] = (timestamp, dispatch_type)
        elif evt_type == "DISPATCH_END":
            if uniq_key in dispatch_start_times:
                start_ts, d_type = dispatch_start_times.pop(uniq_key)
                dispatch_times_by_type[d_type].append((timestamp - start_ts).total_seconds())
        elif evt_type == "EXECUTION_START":
            execution_start_times[uniq_key] = timestamp
        elif evt_type == "EXECUTION_END":
            if uniq_key in execution_start_times:
                execution_times.append((timestamp - execution_start_times[uniq_key]).total_seconds())
        elif evt_type == "RETRY_START":
            retry_start_times[uniq_key] = timestamp
        elif evt_type == "RETRY_END":
            if uniq_key in retry_start_times:
                retry_times.append((timestamp - retry_start_times[uniq_key]).total_seconds())
        elif evt_type == "AGGREGATION_START":
            aggregation_start_times[uniq_key] = timestamp
            aggregations += 1
        elif evt_type == "AGGREGATION_END":
            if uniq_key in aggregation_start_times:
                aggregation_times.append((timestamp - aggregation_start_times[uniq_key]).total_seconds())
        elif evt_type == "QUEUED" or evt_type == "DEQUEUED":
            queue_ops += 1
            if "queue_depth" in event.get("details", {}):
                qd = event["details"]["queue_depth"]
                queue_depth_sum += qd
                queue_depth_count += 1
                queue_depths.append(qd)
            if evt_type == "QUEUED":
                queue_start_times[uniq_key] = timestamp
            elif evt_type == "DEQUEUED":
                if uniq_key in queue_start_times:
                    wait_time = (timestamp - queue_start_times[uniq_key]).total_seconds()
                    queue_wait_times.append(wait_time)
        elif evt_type == "HANDOFF":
            handoffs += 1
        elif evt_type in ["WORKER_CRASH", "QUEUE_STALL", "RETRY_ATTEMPT", "TIMEOUT_HIT"]:
            if evt_type == "WORKER_CRASH": worker_crashes += 1
            elif evt_type == "QUEUE_STALL": queue_stalls += 1
            elif evt_type == "RETRY_ATTEMPT": retry_attempts += 1
            elif evt_type == "TIMEOUT_HIT": timeouts_hit += 1
            root_cause = event.get("details", {}).get("root_cause")
            if root_cause:
                failure_root_causes[root_cause] += 1
        elif evt_type == "RETRY":
            retries += 1
        elif evt_type == "TIMEOUT":
            timeouts += 1
        elif evt_type == "CRASH":
            crashes += 1
        elif evt_type == "API_429_ERROR":
            api_429_errors += 1
        elif evt_type == "PROFILING":
            metric_name = event.get("details", {}).get("metric")
            value_ms = event.get("details", {}).get("value_ms")
            if metric_name and value_ms is not None:
                if metric_name not in profiling_data:
                    profiling_data[metric_name] = []
                profiling_data[metric_name].append(value_ms)
            
        if evt_type in ["INFERENCE_START", "EXECUTION_START"] and event.get("worker_id"):
            active_workers[event.get("worker_id")] += 1
            max_active_workers = max(max_active_workers, len([w for w, c in active_workers.items() if c > 0]))
        elif evt_type in ["INFERENCE_END", "EXECUTION_END"] and event.get("worker_id"):
            worker_id = event.get("worker_id")
            if active_workers[worker_id] > 0:
                active_workers[worker_id] -= 1

    p50_latency = statistics.median(request_latencies) if request_latencies else 0.0
    p95_latency = statistics.quantiles(request_latencies, n=100)[94] if len(request_latencies) > 1 else (request_latencies[0] if request_latencies else 0.0)
    p99_latency = statistics.quantiles(request_latencies, n=100)[98] if len(request_latencies) > 1 else (request_latencies[0] if request_latencies else 0.0)
    
    avg_queue_wait = statistics.mean(queue_wait_times) if queue_wait_times else 0.0
    
    avg_dispatch_times = {f"avg_dispatch_{k}_sec": (statistics.mean(v) if v else 0.0) for k, v in dispatch_times_by_type.items()}
    
    avg_execution_time = statistics.mean(execution_times) if execution_times else 0.0
    avg_aggregation_time = statistics.mean(aggregation_times) if aggregation_times else 0.0
    avg_retry_delay = statistics.mean(retry_times) if retry_times else 0.0
    
    avg_queue_depth = (queue_depth_sum / queue_depth_count) if queue_depth_count > 0 else 0.0
    max_queue_depth = max(queue_depths) if queue_depths else 0.0
    p95_queue_depth = statistics.quantiles(queue_depths, n=100)[94] if len(queue_depths) > 1 else (queue_depths[0] if queue_depths else 0.0)
    
    throughput = (completed_requests / total_duration_sec) if total_duration_sec > 0 else 0.0

    result = {
        "run_name": run_name,
        "architecture": architecture,
        "task_type": run_metadata.get("experiment", {}).get("task_type", "unknown"),
        "worker_count": run_metadata.get("experiment", {}).get("worker_count", 0),
        "git_commit": run_metadata.get("experiment", {}).get("git_commit", "unknown"),
        "experiment_version": run_metadata.get("experiment", {}).get("experiment_version", "unknown"),
        "failure_mode": run_metadata.get("failure_injection", {}).get("mode", "none"),
        "straggler_delay_ms": run_metadata.get("failure_injection", {}).get("straggler_delay_ms", 0),
        "total_requests": len(request_start_times),
        "completed_requests": completed_requests,
        "total_duration_sec": total_duration_sec,
        "throughput_req_per_sec": throughput,
        "p50_latency_sec": p50_latency,
        "p95_latency_sec": p95_latency,
        "p99_latency_sec": p99_latency,
        "avg_queue_wait_sec": avg_queue_wait,
        "avg_execution_time_sec": avg_execution_time,
        "avg_aggregation_time_sec": avg_aggregation_time,
        "avg_retry_delay_sec": avg_retry_delay,
        "total_queue_ops": queue_ops,
        "total_handoffs": handoffs,
        "total_aggregations": aggregations,
        "avg_queue_depth": avg_queue_depth,
        "max_queue_depth": max_queue_depth,
        "p95_queue_depth": p95_queue_depth,
        "worker_crashes": worker_crashes,
        "queue_stalls": queue_stalls,
        "retry_attempts": retry_attempts,
        "timeouts_hit": timeouts_hit,
        "failure_root_causes": json.dumps(dict(failure_root_causes)),
        "retries": retries,
        "timeouts": timeouts,
        "crashes": crashes,
        "api_429_errors": api_429_errors,
        "max_active_workers": max_active_workers,
        "avg_master_aggregation_duration_ms": statistics.mean(profiling_data["master_aggregation_duration_ms"]) if "master_aggregation_duration_ms" in profiling_data and profiling_data["master_aggregation_duration_ms"] else 0.0,
        "avg_queue_lock_wait_ms": statistics.mean(profiling_data["queue_lock_wait_ms"]) if "queue_lock_wait_ms" in profiling_data and profiling_data["queue_lock_wait_ms"] else 0.0
    }
    
    result.update(avg_dispatch_times)
    return result

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
