import argparse
import pandas as pd
import numpy as np
from pathlib import Path

def bootstrap_ci(data, num_resamples=1000, ci=95):
    """
    Calculates the bootstrap confidence interval for the mean of the data.
    """
    if len(data) < 2:
        return 0.0, 0.0
    
    resampled_means = []
    n = len(data)
    for _ in range(num_resamples):
        sample = np.random.choice(data, size=n, replace=True)
        resampled_means.append(np.mean(sample))
        
    lower_bound = np.percentile(resampled_means, (100 - ci) / 2.0)
    upper_bound = np.percentile(resampled_means, 100 - (100 - ci) / 2.0)
    
    return lower_bound, upper_bound

def build_dataset(input_csv: str, output_csv: str):
    df = pd.read_csv(input_csv)
    
    # We group by the configuration: architecture, task_type, worker_count, total_requests
    group_cols = ["architecture", "task_type", "worker_count", "total_requests"]
    
    # Metrics to summarize
    metrics = [
        "throughput_req_per_sec", 
        "p50_latency_sec", 
        "p95_latency_sec", 
        "p99_latency_sec", 
        "avg_queue_wait_sec",
        "utilization_busy",
        "utilization_idle",
        "utilization_blocked"
    ]
    
    records = []
    
    for name, group in df.groupby(group_cols):
        arch, task, workers, reqs = name
        
        record = {
            "architecture": arch,
            "task_type": task,
            "worker_count": workers,
            "total_requests": reqs,
            "iterations": len(group)
        }
        
        for metric in metrics:
            if metric not in group.columns:
                continue
                
            data = group[metric].dropna().values
            if len(data) == 0:
                continue
                
            mean_val = np.mean(data)
            median_val = np.median(data)
            variance_val = np.var(data, ddof=1) if len(data) > 1 else 0.0
            iqr_val = np.percentile(data, 75) - np.percentile(data, 25)
            
            ci_lower, ci_upper = bootstrap_ci(data, num_resamples=1000, ci=95)
            
            record[f"{metric}_mean"] = mean_val
            record[f"{metric}_median"] = median_val
            record[f"{metric}_variance"] = variance_val
            record[f"{metric}_iqr"] = iqr_val
            record[f"{metric}_ci_lower"] = ci_lower
            record[f"{metric}_ci_upper"] = ci_upper
            
        records.append(record)
        
    out_df = pd.DataFrame(records)
    out_df.to_csv(output_csv, index=False)
    print(f"Dataset successfully built and saved to {output_csv}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_csv", type=str, required=True, help="Path to the summary CSV from batch_run_phase2a")
    parser.add_argument("--output_csv", type=str, required=True, help="Path to the output benchmark dataset CSV")
    args = parser.parse_args()
    
    build_dataset(args.input_csv, args.output_csv)
