"""
swarm_bottleneck_analyzer.py

Swarm 아키텍처의 병목이 라우팅에 있는지 검증하기 위한 사전 분석 스크립트.

주요 분석 항목:
1. 동시 Busy Agent 수 분포 (Task A, Task B)
2. 전체 실행 시간 중 주요 단계별 소요 시간 비율 (LLM 추론, 라우팅/Handoff)

사용법:
    python analyzer/swarm_bottleneck_analyzer.py --log logs/events.jsonl
"""

import argparse
import json
import collections
from datetime import datetime

def parse_isoformat(ts_str):
    if not ts_str:
        return 0.0
    try:
        # Python 3.11+ supports fromisoformat with Z
        return datetime.fromisoformat(ts_str.replace('Z', '+00:00')).timestamp()
    except ValueError:
        # Fallback
        import dateutil.parser
        return dateutil.parser.isoparse(ts_str).timestamp()

def analyze_log(log_path):
    events = []
    with open(log_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    
    # 시간순 정렬
    events.sort(key=lambda x: x.get('timestamp', ''))

    # 1. 동시 Busy Agent 분포 계산
    busy_agents = set()
    last_ts = None
    busy_distribution = collections.defaultdict(float)
    
    # 2. 비용 구성 계산용 변수
    inference_start_times = {}
    dispatch_start_times = {}
    
    total_inference_time = 0.0
    total_routing_time = 0.0

    system_start = None
    system_end = None

    for event in events:
        ts = parse_isoformat(event.get('timestamp'))
        if not ts:
            continue

        if system_start is None:
            system_start = ts
        system_end = ts

        # Busy Agent 추적
        if event['event_type'] == 'WORKER_STATE':
            if last_ts is not None:
                duration = ts - last_ts
                busy_distribution[len(busy_agents)] += duration
            
            state = event.get('details', {}).get('state')
            worker_id = event.get('worker_id')
            if state == 'busy':
                busy_agents.add(worker_id)
            elif state in ['idle', 'blocked']:
                if worker_id in busy_agents:
                    busy_agents.remove(worker_id)
            
            last_ts = ts

        # Inference 추적
        if event['event_type'] == 'INFERENCE_START':
            task_id = event.get('task_id')
            inference_start_times[task_id] = ts
        elif event['event_type'] == 'INFERENCE_END':
            task_id = event.get('task_id')
            if task_id in inference_start_times:
                total_inference_time += (ts - inference_start_times.pop(task_id))

        # Routing/Handoff 추적
        if event['event_type'] == 'DISPATCH_START':
            task_id = event.get('task_id')
            dispatch_start_times[task_id] = ts
        elif event['event_type'] == 'DISPATCH_END':
            task_id = event.get('task_id')
            if task_id in dispatch_start_times:
                total_routing_time += (ts - dispatch_start_times.pop(task_id))

    # 마지막 구간 처리
    if last_ts is not None and system_end is not None:
        busy_distribution[len(busy_agents)] += (system_end - last_ts)

    # 결과 출력
    total_wall_time = (system_end - system_start) if system_end and system_start else 0.0
    
    print("=" * 50)
    print("1. Concurrent Busy Agent Distribution")
    print("=" * 50)
    total_busy_tracked_time = sum(busy_distribution.values())
    if total_busy_tracked_time > 0:
        for count in sorted(busy_distribution.keys()):
            pct = (busy_distribution[count] / total_busy_tracked_time) * 100
            print(f"  {count} agent(s) busy: {pct:6.2f}% ({busy_distribution[count]:.2f}s)")
    else:
        print("  No WORKER_STATE events found.")

    print("\n" + "=" * 50)
    print("2. Time Breakdown (Critical Path vs Total Agent Time)")
    print("=" * 50)
    print(f"  Total Wall-clock Time: {total_wall_time:.4f}s")
    print(f"  Total LLM Inference (Sum of all agents): {total_inference_time:.4f}s")
    print(f"  Total Routing/Handoff (Sum of all agents): {total_routing_time:.4f}s")
    
    # 만약 LLM Inference가 병렬로 실행되었다면, Wall-clock을 초과할 수 있음.
    # 단일 에이전트 순차 실행(Task B)이라면 Wall-clock과 유사해야 함.
    print(f"\n  Inference as % of Wall-clock: {(total_inference_time / total_wall_time * 100) if total_wall_time > 0 else 0:.1f}%")
    print(f"  Routing as % of Wall-clock  : {(total_routing_time / total_wall_time * 100) if total_wall_time > 0 else 0:.1f}%")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, help="Path to events.jsonl")
    args = parser.parse_args()
    analyze_log(args.log)
