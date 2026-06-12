import os
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

def parse_isoformat(ts_str):
    if not ts_str:
        return 0.0
    try:
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00')).timestamp()
    except ValueError:
        import dateutil.parser
        return dateutil.parser.isoparse(ts_str).timestamp()

def extract_metrics_from_log(log_path):
    events = []
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    events.append(json.loads(line))
    except Exception as e:
        return None

    if not events:
        return None

    events.sort(key=lambda x: x.get('timestamp', ''))

    system_start_ts = parse_isoformat(events[0].get('timestamp'))
    system_end_ts = parse_isoformat(events[-1].get('timestamp'))
    worker_states = {}

    for event in events:
        ts = parse_isoformat(event.get('timestamp'))
        if not ts:
            continue

        evt_type = event.get('event_type')
        worker_id = event.get('worker_id')
            
        if evt_type == 'WORKER_STATE' and worker_id:
            state = event.get('details', {}).get('state')
            if worker_id not in worker_states:
                worker_states[worker_id] = {'last_ts': ts, 'state': state, 'busy': 0.0, 'idle': 0.0, 'blocked': 0.0}
            else:
                prev = worker_states[worker_id]
                duration = ts - prev['last_ts']
                if prev['state'] in ['busy', 'idle', 'blocked']:
                    prev[prev['state']] += duration
                prev['state'] = state
                prev['last_ts'] = ts

    metadata_path = Path(log_path).parent / "metadata.json"
    if not metadata_path.exists():
        return None
        
    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    except:
        return None

    task_type = metadata.get('experiment', {}).get('task_type')
    if not task_type:
        return None 
        
    run_id = metadata.get('run_id', '')
    if '_monolithic_' in run_id:
        arch = 'monolithic'
    elif '_master_worker_' in run_id:
        arch = 'master_worker'
    elif '_queue_based_' in run_id:
        arch = 'queue_based'
    elif '_swarm_' in run_id:
        arch = 'swarm'
    else:
        return None
        
    failure_mode = metadata.get('failure_injection', {}).get('mode', 'none')

    if not system_start_ts or not system_end_ts:
        return None

    for worker_id, prev in worker_states.items():
        if prev['state'] in ['busy', 'idle', 'blocked']:
            duration = system_end_ts - prev['last_ts']
            if duration > 0:
                prev[prev['state']] += duration

    total_busy = sum(w['busy'] for w in worker_states.values())
    total_idle = sum(w['idle'] for w in worker_states.values())
    total_blocked = sum(w['blocked'] for w in worker_states.values())
    
    total_worker_time = total_busy + total_idle + total_blocked
    if total_worker_time == 0:
        total_worker_time = 1.0

    return {
        'exp_name': run_id,
        'architecture': arch,
        'task_type': task_type,
        'failure_mode': failure_mode,
        'wall_clock_time': system_end_ts - system_start_ts,
        'util_busy_pct': (total_busy / total_worker_time) * 100,
        'util_idle_pct': (total_idle / total_worker_time) * 100,
        'util_blocked_pct': (total_blocked / total_worker_time) * 100,
    }

def main():
    logs_dir = Path("result4/runs")
    results = []
    
    if not logs_dir.exists():
        print(f"Directory {logs_dir} not found.")
        return

    print(f"Extracting data from {logs_dir}...")
    for run_dir in os.listdir(logs_dir):
        log_path = logs_dir / run_dir / "events.jsonl"
        if log_path.exists():
            metrics = extract_metrics_from_log(log_path)
            if metrics:
                results.append(metrics)
                
    if not results:
        print("No valid experiment logs found.")
        return

    df = pd.DataFrame(results)
    
    summary_df = df.groupby(['architecture', 'task_type', 'failure_mode']).agg({
        'wall_clock_time': ['mean', 'std', 'count'],
        'util_busy_pct': 'mean',
        'util_idle_pct': 'mean',
        'util_blocked_pct': 'mean'
    }).reset_index()
    
    summary_df.columns = ['_'.join(col).strip('_') for col in summary_df.columns.values]
    
    out_dir = Path("results/final")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    summary_df.to_csv(out_dir / "aggregated_results.csv", index=False)
    print(f"Extracted data saved to {out_dir / 'aggregated_results.csv'}")
    print("\nSummary Preview:")
    print(summary_df.head(10))

if __name__ == "__main__":
    main()
