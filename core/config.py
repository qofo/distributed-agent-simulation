import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

@dataclass
class RetryPolicyConfig:
    enabled: bool = False
    max_retries: int = 0

@dataclass
class FailureInjectionConfig:
    mode: str = "none" # none, crash, straggler
    target_worker_id: Optional[str] = None
    timing_ms: int = 0
    straggler_delay_ms: int = 0

@dataclass
class WorkloadConfig:
    chunk_count: int = 1
    dataset_path: str = ""

@dataclass
class SimulationConfig:
    mock_inference_latency_ms: int = 0
    timeout_threshold_ms: int = 5000
    retry_policy: RetryPolicyConfig = field(default_factory=RetryPolicyConfig)

@dataclass
class ExperimentConfig:
    name: str = "default_run"
    architecture: str = "monolithic"
    worker_count: int = 1
    task_type: str = "A"

@dataclass
class GlobalConfig:
    experiment: ExperimentConfig = field(default_factory=ExperimentConfig)
    workload: WorkloadConfig = field(default_factory=WorkloadConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    failure_injection: FailureInjectionConfig = field(default_factory=FailureInjectionConfig)

def load_config(file_path: str) -> GlobalConfig:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {file_path}")

    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    if 'experiment' not in data:
        raise ValueError("Invalid config: 'experiment' block is required.")

    # Parse nested structures manually to fail fast on invalid inputs
    exp_data = data.get('experiment', {})
    workload_data = data.get('workload', {})
    sim_data = data.get('simulation', {})
    fail_data = data.get('failure_injection', {})

    retry_data = sim_data.get('retry_policy', {})
    retry_policy = RetryPolicyConfig(
        enabled=retry_data.get('enabled', False),
        max_retries=retry_data.get('max_retries', 0)
    )

    simulation = SimulationConfig(
        mock_inference_latency_ms=sim_data.get('mock_inference_latency_ms', 0),
        timeout_threshold_ms=sim_data.get('timeout_threshold_ms', 5000),
        retry_policy=retry_policy
    )

    failure_injection = FailureInjectionConfig(
        mode=fail_data.get('mode', 'none'),
        target_worker_id=fail_data.get('target_worker_id'),
        timing_ms=fail_data.get('timing_ms', 0),
        straggler_delay_ms=fail_data.get('straggler_delay_ms', 0)
    )

    workload = WorkloadConfig(
        chunk_count=workload_data.get('chunk_count', 1),
        dataset_path=workload_data.get('dataset_path', '')
    )

    experiment = ExperimentConfig(
        name=exp_data.get('name', 'default_run'),
        architecture=exp_data.get('architecture', 'monolithic'),
        worker_count=exp_data.get('worker_count', 1),
        task_type=exp_data.get('task_type', 'A')
    )

    return GlobalConfig(
        experiment=experiment,
        workload=workload,
        simulation=simulation,
        failure_injection=failure_injection
    )
