from enum import Enum
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

class EventType(str, Enum):
    TASK_RECEIVED = "TASK_RECEIVED"
    TASK_COMPLETED = "TASK_COMPLETED"
    
    QUEUED = "QUEUED"
    DEQUEUED = "DEQUEUED"
    
    INFERENCE_START = "INFERENCE_START"
    INFERENCE_END = "INFERENCE_END"
    
    TIMEOUT = "TIMEOUT"
    RETRY = "RETRY"
    CRASH = "CRASH"
    RECOVERY = "RECOVERY"
    
    AGGREGATION_START = "AGGREGATION_START"
    AGGREGATION_END = "AGGREGATION_END"
    HANDOFF = "HANDOFF"
    
    DISPATCH_START = "DISPATCH_START"
    DISPATCH_END = "DISPATCH_END"
    
    EXECUTION_START = "EXECUTION_START"
    EXECUTION_END = "EXECUTION_END"
    
    RETRY_START = "RETRY_START"
    RETRY_END = "RETRY_END"
    
    RUN_METADATA = "RUN_METADATA"
    
    WORKER_CRASH = "WORKER_CRASH"
    QUEUE_STALL = "QUEUE_STALL"
    RETRY_ATTEMPT = "RETRY_ATTEMPT"
    TIMEOUT_HIT = "TIMEOUT_HIT"

    API_429_ERROR = "API_429_ERROR"
    PROFILING = "PROFILING"
    WORKER_STATE = "WORKER_STATE"
    LLM_RESPONSE = "LLM_RESPONSE"

@dataclass
class LogEvent:
    trace_id: str
    architecture: str
    task_id: str
    event_type: EventType
    worker_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert the event to a dictionary suitable for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "trace_id": self.trace_id,
            "architecture": self.architecture,
            "task_id": self.task_id,
            "event_type": self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            "worker_id": self.worker_id,
            "details": self.details,
        }
