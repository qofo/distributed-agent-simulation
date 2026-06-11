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
    
    # run_name is like sweep_monolithic_W1_L10 or sweep_queue_based_W4_L500
    df['architecture'] = df['run_name'].apply(lambda x: x.split('_W')[0].replace('sweep_', ''))
    df['latency_ms'] = df['run_name'].apply(lambda x: int(x.split('_L')[1]))
    
    # Sort
    df = df.sort_values(by=['architecture', 'latency_ms'])
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    plt.figure(figsize=(10, 6))
    
    mono_df = df[df['architecture'] == 'monolithic']
    queue_df = df[df['architecture'] == 'queue_based']
    
    plt.plot(mono_df['latency_ms'], mono_df['throughput_req_per_sec'], marker='o', label='Monolithic (W1)')
    plt.plot(queue_df['latency_ms'], queue_df['throughput_req_per_sec'], marker='x', label='Queue-Based (W4)')
    
    plt.xscale('log')
    plt.yscale('log')
    
    plt.title('Inference Latency vs Throughput (Threshold Search)')
    plt.xlabel('Inference Latency (ms) [Log Scale]')
    plt.ylabel('Throughput (req/sec) [Log Scale]')
    plt.grid(True, which="both", ls="-", alpha=0.2)
    plt.legend()
    
    chart_path = output_dir / 'threshold_chart.png'
    plt.savefig(chart_path)
    plt.close()
    
    md_path = output_dir / "sweep_summary.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Sweep Latency Experiment Report\n\n")
        f.write("## 1. Overview\n")
        f.write(f"Generated from batch: `{batch_dir.name}`\n\n")
        f.write("## 2. Chart\n")
        f.write(f"![Threshold]({chart_path.name})\n\n")
        f.write("## 3. Data\n")
        display_df = df[['architecture', 'latency_ms', 'throughput_req_per_sec', 'p50_latency_sec']].round(3)
        f.write(display_df.to_markdown(index=False) + "\n")
        
    print(f"Sweep report generated at {md_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch_dir", required=True, type=str)
    parser.add_argument("--output_dir", type=str, default="reports/sweep")
    args = parser.parse_args()
    
    out_path = Path(args.output_dir)
    if not out_path.is_absolute():
        out_path = Path.cwd() / args.output_dir
        
    generate_report(Path(args.batch_dir), out_path)
