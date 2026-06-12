import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
import os
import json

def load_data(csv_path):
    if not Path(csv_path).exists():
        print(f"Error: {csv_path} does not exist.")
        sys.exit(1)
    return pd.read_csv(csv_path)

def plot_baseline_comparison(df, out_dir):
    # Filter for baseline (no failure)
    df_baseline = df[df['failure_mode'] == 'none'].copy()
    
    if df_baseline.empty:
        return

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
    
    for task in ['A', 'B', 'C']:
        df_task = df_baseline[df_baseline['task_type'] == task]
        if df_task.empty:
            continue
            
        df_task = df_task.set_index('architecture')
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
    for task in ['A', 'B', 'C']:
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

def get_run_metadata(run_dir):
    events_file = run_dir / "events.jsonl"
    if not events_file.exists():
        return None
    try:
        with open(events_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    if data.get('event_type') == 'SYSTEM_START':
                        return data.get('details', {}).get('config', {})
    except:
        pass
    return None

def plot_queue_backlog(logs_dir, out_dir):
    samples = {}
    if not logs_dir.exists():
        return
    for run_name in os.listdir(logs_dir):
        run_dir = logs_dir / run_name
        config = get_run_metadata(run_dir)
        if not config:
            continue
        arch = config.get('experiment', {}).get('architecture')
        task = config.get('experiment', {}).get('task_type')
        fail_mode = config.get('failure_injection', {}).get('mode')
        
        if fail_mode == 'none':
            key = (arch, task)
            if key not in samples:
                ts_file = run_dir / "timeseries_queue.csv"
                if ts_file.exists():
                    samples[key] = pd.read_csv(ts_file)
                    
    for task in ['A', 'B', 'C']:
        plt.figure(figsize=(10, 6))
        plotted = False
        for (arch, t), df in samples.items():
            if t == task and not df.empty:
                plt.plot(df['relative_time'], df['queue_len'], label=arch, alpha=0.8)
                plotted = True
        
        if plotted:
            plt.title(f'Queue Backlog Timeline - Task {task}')
            plt.ylabel('Queue Length')
            plt.xlabel('Time (seconds)')
            plt.legend(title='Architecture')
            plt.tight_layout()
            plt.savefig(out_dir / f'queue_backlog_timeline_task_{task}.png')
        plt.close()

def plot_throughput_timeline(logs_dir, out_dir):
    samples = {}
    if not logs_dir.exists():
        return
    for run_name in os.listdir(logs_dir):
        run_dir = logs_dir / run_name
        config = get_run_metadata(run_dir)
        if not config:
            continue
        arch = config.get('experiment', {}).get('architecture')
        task = config.get('experiment', {}).get('task_type')
        fail_mode = config.get('failure_injection', {}).get('mode')
        
        if fail_mode == 'none':
            key = (arch, task)
            if key not in samples:
                ts_file = run_dir / "timeseries_throughput.csv"
                if ts_file.exists():
                    samples[key] = pd.read_csv(ts_file)
                    
    for task in ['A', 'B', 'C']:
        plt.figure(figsize=(10, 6))
        plotted = False
        for (arch, t), df in samples.items():
            if t == task and not df.empty:
                plt.plot(df['relative_time'], df['throughput'], label=arch, alpha=0.8)
                plotted = True
        
        if plotted:
            plt.title(f'Throughput Timeline - Task {task}')
            plt.ylabel('Tasks Completed per Second')
            plt.xlabel('Time (seconds)')
            plt.legend(title='Architecture')
            plt.tight_layout()
            plt.savefig(out_dir / f'throughput_timeline_task_{task}.png')
        plt.close()

def plot_failure_impact_detail(df, out_dir):
    if 'throughput_drop_pct_mean' not in df.columns:
        return
        
    df_crash = df[df['failure_mode'] == 'crash'].copy()
    if df_crash.empty:
        return
        
    for task in ['A', 'B', 'C']:
        df_task = df_crash[df_crash['task_type'] == task].copy()
        if df_task.empty:
            continue
            
        plt.figure(figsize=(10, 6))
        sns.barplot(data=df_task, x='architecture', y='throughput_drop_pct_mean')
        plt.title(f'Throughput Drop After Crash - Task {task}')
        plt.ylabel('Throughput Drop (%)')
        plt.xlabel('Architecture')
        plt.tight_layout()
        plt.savefig(out_dir / f'throughput_drop_task_{task}.png')
        plt.close()

def plot_queue_metrics(df, out_dir):
    if 'avg_queue_wait_ms_mean' not in df.columns:
        return
    df_baseline = df[df['failure_mode'] == 'none'].copy()
    
    for task in ['A', 'B', 'C']:
        df_task = df_baseline[df_baseline['task_type'] == task].copy()
        if df_task.empty:
            continue
            
        plt.figure(figsize=(10, 6))
        sns.barplot(data=df_task, x='architecture', y='avg_queue_wait_ms_mean')
        plt.title(f'Average Queue Wait Time - Task {task}')
        plt.ylabel('Queue Wait Time (ms)')
        plt.xlabel('Architecture')
        plt.tight_layout()
        plt.savefig(out_dir / f'queue_wait_time_task_{task}.png')
        plt.close()

def main():
    csv_path = Path("results/final/aggregated_results.csv")
    out_dir = Path("results/final/plots")
    out_dir.mkdir(parents=True, exist_ok=True)
    logs_dir = Path("logs/runs")
    
    if csv_path.exists():
        df = load_data(csv_path)
        print("Generating Baseline Comparison Plot...")
        plot_baseline_comparison(df, out_dir)
        print("Generating Worker Utilization Plots...")
        plot_worker_utilization(df, out_dir)
        print("Generating Failure Impact Plots...")
        plot_failure_impact(df, out_dir)
        print("Generating Detailed Failure Drop Plots...")
        plot_failure_impact_detail(df, out_dir)
        print("Generating Queue Wait Time Plots...")
        plot_queue_metrics(df, out_dir)
    else:
        print(f"Warning: {csv_path} not found. Skipping aggregated plots.")
        
    print("Generating Timeseries Plots...")
    plot_queue_backlog(logs_dir, out_dir)
    plot_throughput_timeline(logs_dir, out_dir)
    print(f"All plots saved to {out_dir}")

if __name__ == "__main__":
    main()
