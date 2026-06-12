import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys

def load_data(csv_path):
    if not Path(csv_path).exists():
        print(f"Error: {csv_path} does not exist.")
        sys.exit(1)
    return pd.read_csv(csv_path)

def plot_baseline_comparison(df, out_dir):
    # Filter for baseline (no failure)
    df_baseline = df[df['failure_mode'] == 'none'].copy()
    
    plt.figure(figsize=(10, 6))
    sns.barplot(data=df_baseline, x='architecture', y='wall_clock_time_mean', hue='task_type')
    plt.title('Baseline Wall-clock Time by Architecture and Task Type')
    plt.ylabel('Wall-clock Time (seconds)')
    plt.xlabel('Architecture')
    plt.tight_layout()
    plt.savefig(out_dir / 'baseline_comparison.png')
    plt.close()

def plot_worker_utilization(df, out_dir):
    df_baseline = df[df['failure_mode'] == 'none'].copy()
    
    # We want a stacked bar chart. 
    # Let's create one plot per task type, or side-by-side.
    for task in ['A', 'B']:
        df_task = df_baseline[df_baseline['task_type'] == task].set_index('architecture')
        if df_task.empty:
            continue
            
        df_plot = df_task[['util_busy_pct_mean', 'util_blocked_pct_mean', 'util_idle_pct_mean']]
        df_plot.columns = ['Busy', 'Blocked (LLM)', 'Idle']
        
        ax = df_plot.plot(kind='bar', stacked=True, figsize=(8, 6), color=['#2ca02c', '#ff7f0e', '#d62728'])
        plt.title(f'Worker Utilization - Task {task}')
        plt.ylabel('Percentage (%)')
        plt.xlabel('Architecture')
        plt.legend(title='State', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(out_dir / f'utilization_task_{task}.png')
        plt.close()

def plot_failure_impact(df, out_dir):
    # We want to compare wall-clock time for none, crash, straggler across architectures.
    for task in ['A', 'B']:
        df_task = df[df['task_type'] == task].copy()
        if df_task.empty:
            continue
            
        plt.figure(figsize=(12, 6))
        sns.barplot(data=df_task, x='architecture', y='wall_clock_time_mean', hue='failure_mode')
        plt.title(f'Failure Impact on Wall-clock Time - Task {task}')
        plt.ylabel('Wall-clock Time (seconds)')
        plt.xlabel('Architecture')
        plt.legend(title='Failure Mode')
        plt.tight_layout()
        plt.savefig(out_dir / f'failure_impact_task_{task}.png')
        plt.close()

def main():
    csv_path = Path("results/final/aggregated_results.csv")
    out_dir = Path("results/final/plots")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    df = load_data(csv_path)
    print("Generating Baseline Comparison Plot...")
    plot_baseline_comparison(df, out_dir)
    print("Generating Worker Utilization Plots...")
    plot_worker_utilization(df, out_dir)
    print("Generating Failure Impact Plots...")
    plot_failure_impact(df, out_dir)
    print(f"All plots saved to {out_dir}")

if __name__ == "__main__":
    main()
