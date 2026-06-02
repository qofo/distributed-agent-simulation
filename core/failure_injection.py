from core.config import GlobalConfig
from core.log_schema import LogEvent, EventType


class CrashSimulationError(Exception):
    """워커 크래시를 시뮬레이션하기 위한 예외."""
    pass


import random

def get_effective_latency(config: GlobalConfig, worker_id: str) -> float:
    """
    Returns the effective inference latency in seconds for a given worker.
    Includes base latency, TTFT + token jitter, and any configured straggler delay.
    """
    base = config.simulation.mock_inference_latency_ms / 1000.0
    
    # Simulate TTFT (Time To First Token) and variable token lengths
    ttft = base * 0.3
    token_time = base * 0.7
    
    # Jitter represents variability in generation length (+- 30%)
    jitter = random.uniform(-0.3, 0.3) * token_time
    
    base_latency_sec = max(0.01, ttft + token_time + jitter) # Ensure it's never 0

    if config.failure_injection.mode == "straggler":
        target = config.failure_injection.target_worker_id
        if target is not None and target == worker_id:
            return base_latency_sec + (config.failure_injection.straggler_delay_ms / 1000.0)

    return base_latency_sec


def check_crash(config: GlobalConfig, worker_id: str, logger, trace_id: str, architecture: str, task_id: str):
    """
    Crash injection 체크.
    config에 crash 모드가 설정되어 있고 대상 워커가 일치하면,
    CRASH 이벤트를 로그에 기록하고 CrashSimulationError를 발생시킨다.
    """
    if config.failure_injection.mode == "crash":
        target = config.failure_injection.target_worker_id
        if target is not None and target == worker_id:
            logger.error_crash(trace_id, architecture, task_id, worker_id, "Simulated crash injection")
            raise CrashSimulationError(f"Worker {worker_id} crashed (simulated)")
