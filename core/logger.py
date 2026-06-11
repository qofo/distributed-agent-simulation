import json
import logging
import threading
from typing import Any, Dict, Optional
from pathlib import Path

from core.log_schema import LogEvent, EventType

class JSONLinesFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # The record.msg is expected to be a LogEvent dictionary or object
        if isinstance(record.msg, LogEvent):
            return json.dumps(record.msg.to_dict())
        elif isinstance(record.msg, dict):
            return json.dumps(record.msg)
        return json.dumps({"message": str(record.msg)})

class StructuredLogger:
    _instances = {}
    _lock = threading.Lock()

    def __new__(cls, name: str, log_file: Optional[str] = None, disabled: bool = False):
        """Implement a thread-safe singleton pattern per logger name."""
        with cls._lock:
            if name not in cls._instances:
                instance = super(StructuredLogger, cls).__new__(cls)
                cls._instances[name] = instance
                instance._init_logger(name, log_file)
                instance._disabled = disabled
            else:
                instance = cls._instances[name]
                instance._disabled = disabled
            return cls._instances[name]

    def _init_logger(self, name: str, log_file: Optional[str]):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Avoid adding multiple handlers if already initialized
        if not self.logger.handlers:
            self.logger.propagate = False
            formatter = JSONLinesFormatter()

            # Optional file handler
            if log_file:
                # Ensure directory exists
                Path(log_file).parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
                file_handler.setFormatter(formatter)
                self.logger.addHandler(file_handler)

            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def log_event(self, event: LogEvent):
        """Log a generic event. No-ops when disabled=True (I/O is skipped but call overhead remains)."""
        if getattr(self, '_disabled', False):
            return
        self.logger.info(event)

    # Helper methods for common events
    def task_received(self, trace_id: str, architecture: str, task_id: str, details: Optional[Dict[str, Any]] = None):
        event = LogEvent(trace_id=trace_id, architecture=architecture, task_id=task_id, 
                         event_type=EventType.TASK_RECEIVED, details=details or {})
        self.log_event(event)

    def task_completed(self, trace_id: str, architecture: str, task_id: str, details: Optional[Dict[str, Any]] = None):
        event = LogEvent(trace_id=trace_id, architecture=architecture, task_id=task_id, 
                         event_type=EventType.TASK_COMPLETED, details=details or {})
        self.log_event(event)

    def inference_start(self, trace_id: str, architecture: str, task_id: str, worker_id: str, details: Optional[Dict[str, Any]] = None):
        event = LogEvent(trace_id=trace_id, architecture=architecture, task_id=task_id, 
                         event_type=EventType.INFERENCE_START, worker_id=worker_id, details=details or {})
        self.log_event(event)

    def inference_end(self, trace_id: str, architecture: str, task_id: str, worker_id: str, latency_ms: int, details: Optional[Dict[str, Any]] = None):
        det = details or {}
        det["latency_ms"] = latency_ms
        event = LogEvent(trace_id=trace_id, architecture=architecture, task_id=task_id, 
                         event_type=EventType.INFERENCE_END, worker_id=worker_id, details=det)
        self.log_event(event)

    def queued(self, trace_id: str, architecture: str, task_id: str, details: Optional[Dict[str, Any]] = None):
        event = LogEvent(trace_id=trace_id, architecture=architecture, task_id=task_id, 
                         event_type=EventType.QUEUED, details=details or {})
        self.log_event(event)

    def dequeued(self, trace_id: str, architecture: str, task_id: str, worker_id: str, details: Optional[Dict[str, Any]] = None):
        event = LogEvent(trace_id=trace_id, architecture=architecture, task_id=task_id, 
                         event_type=EventType.DEQUEUED, worker_id=worker_id, details=details or {})
        self.log_event(event)

    def dispatch_start(self, trace_id: str, architecture: str, task_id: str, worker_id: str, dispatch_type: str):
        self.log_event(LogEvent(trace_id=trace_id, architecture=architecture, task_id=task_id, event_type=EventType.DISPATCH_START, worker_id=worker_id, details={"dispatch_type": dispatch_type}))

    def dispatch_end(self, trace_id: str, architecture: str, task_id: str, worker_id: str, dispatch_type: str):
        self.log_event(LogEvent(trace_id=trace_id, architecture=architecture, task_id=task_id, event_type=EventType.DISPATCH_END, worker_id=worker_id, details={"dispatch_type": dispatch_type}))

    def execution_start(self, trace_id: str, architecture: str, task_id: str, worker_id: str, execution_mode: str):
        self.log_event(LogEvent(trace_id=trace_id, architecture=architecture, task_id=task_id, event_type=EventType.EXECUTION_START, worker_id=worker_id, details={"execution_mode": execution_mode}))

    def execution_end(self, trace_id: str, architecture: str, task_id: str, worker_id: str, execution_mode: str, latency_ms: int):
        self.log_event(LogEvent(trace_id=trace_id, architecture=architecture, task_id=task_id, event_type=EventType.EXECUTION_END, worker_id=worker_id, details={"execution_mode": execution_mode, "latency_ms": latency_ms}))

    def retry_start(self, trace_id: str, architecture: str, task_id: str):
        self.log_event(LogEvent(trace_id=trace_id, architecture=architecture, task_id=task_id, event_type=EventType.RETRY_START))

    def retry_end(self, trace_id: str, architecture: str, task_id: str):
        self.log_event(LogEvent(trace_id=trace_id, architecture=architecture, task_id=task_id, event_type=EventType.RETRY_END))

    def run_metadata(self, trace_id: str, architecture: str, metadata_dict: Dict[str, Any]):
        self.log_event(LogEvent(trace_id=trace_id, architecture=architecture, task_id="system-init", event_type=EventType.RUN_METADATA, details=metadata_dict))

    def worker_crash(self, trace_id: str, architecture: str, task_id: str, worker_id: str, reason: str, root_cause: Optional[str] = None):
        details = {"reason": reason}
        if root_cause:
            details["root_cause"] = root_cause
        self.log_event(LogEvent(trace_id=trace_id, architecture=architecture, task_id=task_id, event_type=EventType.WORKER_CRASH, worker_id=worker_id, details=details))

    def queue_stall(self, trace_id: str, architecture: str, task_id: str, worker_id: str, wait_ms: float, root_cause: Optional[str] = None):
        details = {"wait_ms": wait_ms}
        if root_cause:
            details["root_cause"] = root_cause
        self.log_event(LogEvent(trace_id=trace_id, architecture=architecture, task_id=task_id, event_type=EventType.QUEUE_STALL, worker_id=worker_id, details=details))

    def retry_attempt(self, trace_id: str, architecture: str, task_id: str, worker_id: str, attempt_num: int, reason: str, root_cause: Optional[str] = None):
        details = {"attempt_num": attempt_num, "reason": reason}
        if root_cause:
            details["root_cause"] = root_cause
        self.log_event(LogEvent(trace_id=trace_id, architecture=architecture, task_id=task_id, event_type=EventType.RETRY_ATTEMPT, worker_id=worker_id, details=details))

    def timeout_hit(self, trace_id: str, architecture: str, task_id: str, worker_id: str, elapsed_ms: float, root_cause: Optional[str] = None):
        details = {"elapsed_ms": elapsed_ms}
        if root_cause:
            details["root_cause"] = root_cause
        self.log_event(LogEvent(trace_id=trace_id, architecture=architecture, task_id=task_id, event_type=EventType.TIMEOUT_HIT, worker_id=worker_id, details=details))

    def api_429_error(self, trace_id: str, architecture: str, worker_id: str):
        self.log_event(LogEvent(trace_id=trace_id, architecture=architecture, task_id="api-call", event_type=EventType.API_429_ERROR, worker_id=worker_id))

    def profiling(self, trace_id: str, architecture: str, metric_name: str, value_ms: float, worker_id: Optional[str] = None):
        self.log_event(LogEvent(trace_id=trace_id, architecture=architecture, task_id="profiling", event_type=EventType.PROFILING, worker_id=worker_id, details={"metric": metric_name, "value_ms": value_ms}))

    def worker_state(self, trace_id: str, architecture: str, worker_id: str, state: str, details: Optional[Dict[str, Any]] = None):
        det = details or {}
        det["state"] = state
        self.log_event(LogEvent(trace_id=trace_id, architecture=architecture, task_id="state-transition", event_type=EventType.WORKER_STATE, worker_id=worker_id, details=det))
