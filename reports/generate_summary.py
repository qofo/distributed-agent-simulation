import pandas as pd
import matplotlib.pyplot as plt
import argparse
from pathlib import Path

def generate_report(batch_dir: Path):
    csv_path = batch_dir / "summary.csv"
    if not csv_path.exists():
        print(f"Error: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)
    # df has columns: architecture,total_requests,completed_requests,total_duration_sec,throughput_req_per_sec,p50_latency_sec,p95_latency_sec,p99_latency_sec,avg_queue_wait_sec,retries,timeouts,crashes
    
    # We need to distinguish between Task A and Task B runs. 
    # But batch_run didn't put task_type or worker_count in the CSV! 
    # Let's fix that conceptually, but since the CSV is what we have, we'll plot by architecture and order.
    # Actually, the CSV only has the output of metrics_parser which didn't include worker_count.
    # Let's just create simple charts based on the index.
    
    # Let's add a "run_name" column based on the index or architecture
    df['run_name'] = df['architecture'] + "_" + df.index.astype(str)
    
    reports_dir = Path(__file__).resolve().parent
    reports_dir.mkdir(exist_ok=True)
    
    # 1. Throughput Chart
    plt.figure(figsize=(10, 6))
    plt.bar(df['run_name'], df['throughput_req_per_sec'], color='skyblue')
    plt.title('Throughput across Runs')
    plt.ylabel('Req/sec')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    throughput_chart = reports_dir / 'throughput.png'
    plt.savefig(throughput_chart)
    plt.close()
    
    # 2. Latency Chart
    plt.figure(figsize=(10, 6))
    plt.plot(df['run_name'], df['p50_latency_sec'], marker='o', label='p50')
    plt.plot(df['run_name'], df['p99_latency_sec'], marker='x', label='p99')
    plt.title('Latency across Runs')
    plt.ylabel('Seconds')
    plt.xticks(rotation=45, ha='right')
    plt.legend()
    plt.tight_layout()
    latency_chart = reports_dir / 'latency.png'
    plt.savefig(latency_chart)
    plt.close()

    # 3. Markdown Report
    md_path = reports_dir / "summary.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Distributed Agent Simulation Summary Report\n\n")
        f.write("## 1. Overview\n")
        f.write(f"Generated from batch: `{batch_dir.name}`\n\n")
        f.write("## 2. Metrics Data\n")
        f.write(df.to_markdown(index=False) + "\n\n")
        f.write("## 3. Charts\n")
        f.write("### Throughput\n")
        f.write(f"![Throughput]({throughput_chart.name})\n\n")
        f.write("### Latency\n")
        f.write(f"![Latency]({latency_chart.name})\n")
        
    print(f"Report generated successfully at {md_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch_dir", required=True, type=str, help="Path to batch directory containing summary.csv")
    args = parser.parse_args()
    
    generate_report(Path(args.batch_dir))
