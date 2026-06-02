import pandas as pd
import matplotlib.pyplot as plt
import argparse
from pathlib import Path

def generate_report(batch_dir: Path, output_dir: Path):
    csv_path = batch_dir / "summary.csv"
    if not csv_path.exists():
        print(f"Error: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)
    # df has columns: architecture,total_requests,completed_requests,total_duration_sec,throughput_req_per_sec,p50_latency_sec,p95_latency_sec,p99_latency_sec,avg_queue_wait_sec,retries,timeouts,crashes
    
    # Group by run_name to calculate mean and standard deviation across iterations
    agg_df = df.groupby('run_name').agg({
        'throughput_req_per_sec': ['mean', 'std'],
        'p50_latency_sec': ['mean', 'std'],
        'p99_latency_sec': ['mean', 'std'],
        'avg_queue_wait_sec': ['mean', 'std']
    }).reset_index()
    
    # Flatten multi-level columns
    agg_df.columns = ['_'.join(col).strip() if col[1] else col[0] for col in agg_df.columns.values]
    
    # Sort for consistent charting
    agg_df = agg_df.sort_values('run_name')
    
    # Output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Throughput Chart
    plt.figure(figsize=(12, 6))
    plt.bar(agg_df['run_name'], agg_df['throughput_req_per_sec_mean'], yerr=agg_df['throughput_req_per_sec_std'], capsize=5, color='skyblue')
    plt.title('Throughput across Configurations (with StdDev)')
    plt.ylabel('Req/sec')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    throughput_chart = output_dir / 'throughput.png'
    plt.savefig(throughput_chart)
    plt.close()
    
    # 2. Latency Chart
    plt.figure(figsize=(12, 6))
    plt.errorbar(agg_df['run_name'], agg_df['p50_latency_sec_mean'], yerr=agg_df['p50_latency_sec_std'], fmt='-o', label='p50 Mean')
    plt.errorbar(agg_df['run_name'], agg_df['p99_latency_sec_mean'], yerr=agg_df['p99_latency_sec_std'], fmt='-x', label='p99 Mean')
    plt.title('Latency across Configurations (with StdDev)')
    plt.ylabel('Seconds')
    plt.xticks(rotation=45, ha='right')
    plt.legend()
    plt.tight_layout()
    latency_chart = output_dir / 'latency.png'
    plt.savefig(latency_chart)
    plt.close()

    # 2.5 Task B Overhead Chart
    task_b_df = agg_df[agg_df['run_name'].str.contains("_TB_")]
    
    overhead_chart = None
    if not task_b_df.empty:
        plt.figure(figsize=(12, 6))
        # Bar 1: Total Latency
        plt.bar(task_b_df['run_name'], task_b_df['p50_latency_sec_mean'], yerr=task_b_df['p50_latency_sec_std'], capsize=5, label='Total Latency (p50)', color='lightgray')
        # Bar 2: Avg Queue Wait (overlay)
        plt.bar(task_b_df['run_name'], task_b_df['avg_queue_wait_sec_mean'], label='Avg Queue Wait Time', color='orange')
        
        plt.title('Communication Overhead in Task B (Sequential Chained Tasks)')
        plt.ylabel('Seconds')
        plt.xticks(rotation=45, ha='right')
        plt.legend()
        plt.tight_layout()
        overhead_chart = output_dir / 'overhead_task_b.png'
        plt.savefig(overhead_chart)
        plt.close()

    # 3. Markdown Report
    md_path = output_dir / "summary.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Distributed Agent Simulation Summary Report\n\n")
        f.write("## 1. Overview\n")
        f.write(f"Generated from batch: `{batch_dir.name}`\n\n")
        f.write("## 2. Aggregate Metrics Data\n")
        # Round the metrics for better display
        display_df = agg_df.round(3)
        f.write(display_df.to_markdown(index=False) + "\n\n")
        f.write("## 3. Charts\n")
        f.write("### Throughput\n")
        f.write(f"![Throughput]({throughput_chart.name})\n\n")
        f.write("### Latency\n")
        f.write(f"![Latency]({latency_chart.name})\n\n")
        if overhead_chart:
            f.write("### Communication Overhead (Task B)\n")
            f.write(f"![Overhead]({overhead_chart.name})\n")
        
    print(f"Report generated successfully at {md_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch_dir", required=True, type=str, help="Path to batch directory containing summary.csv")
    parser.add_argument("--output_dir", type=str, default="reports", help="Directory to save the reports to")
    args = parser.parse_args()
    
    out_path = Path(args.output_dir)
    if not out_path.is_absolute():
        out_path = Path.cwd() / args.output_dir
    
    generate_report(Path(args.batch_dir), out_path)
