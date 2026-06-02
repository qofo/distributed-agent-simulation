import pandas as pd
import matplotlib.pyplot as plt
import argparse
from pathlib import Path

def generate_sweep_chart(batch_dir: Path):
    csv_path = batch_dir / "summary.csv"
    if not csv_path.exists():
        print(f"Error: {csv_path} not found.")
        return

    df = pd.read_csv(csv_path)
    
    # We expect 'name' or 'architecture' in df. But parser only has architecture.
    # To differentiate by latency, we might need to parse the run_name from the folder name, 
    # but currently parser doesn't output latency. 
    # Let's extract latency from run_name if we stored it, or we can just infer from order.
    # The sweep runs: monolithic L10, queue W4 L10, mono L20, queue L20...
    
    # Better: just re-read the configs since summary.csv doesn't have the latency column!
    # Wait, the parser output DOES NOT have latency.
    # We can infer latency by parsing the directory name of the run logs if we had it, but we don't in df.
    
    # Let's assume the CSV rows exactly match LATENCIES_MS * 2.
    LATENCIES_MS = [10, 20, 50, 100, 200, 300, 500]
    
    monolithic_times = []
    queue_times = []
    
    for idx, row in df.iterrows():
        arch = row['architecture']
        if arch == 'monolithic':
            monolithic_times.append(row['total_duration_sec'])
        elif arch == 'queue_based':
            queue_times.append(row['total_duration_sec'])
            
    if len(monolithic_times) != len(LATENCIES_MS) or len(queue_times) != len(LATENCIES_MS):
        print("Data length mismatch. Cannot generate sweep chart.")
        return
        
    reports_dir = Path(__file__).resolve().parent
    reports_dir.mkdir(exist_ok=True)
    
    plt.figure(figsize=(10, 6))
    plt.plot(LATENCIES_MS, monolithic_times, marker='o', label='Monolithic (W=1)')
    plt.plot(LATENCIES_MS, queue_times, marker='x', label='Queue-Based (W=4)')
    
    plt.title('Latency Sweep: Crossover Point (Task A)')
    plt.xlabel('Mock Inference Latency (ms)')
    plt.ylabel('Total Duration (sec)')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    
    chart_path = reports_dir / 'latency_sweep_crossover.png'
    plt.savefig(chart_path)
    plt.close()
    
    print(f"Sweep chart generated at {chart_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch_dir", required=True, type=str, help="Path to sweep batch directory")
    args = parser.parse_args()
    
    generate_sweep_chart(Path(args.batch_dir))
