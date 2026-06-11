"""
NullLogger: 모든 메서드가 즉시 반환하는 no-op 로거.

용도:
    로깅 관련 전체 비용(함수 호출 스택, 인자 계산, 객체 생성 포함)을 측정하기 위한
    3단계 로깅 오버헤드 실험의 실험군 C에 해당한다.

    실험군 A (정상 로깅)  - 실험군 C (NullLogger) = 전체 로깅 관련 오버헤드
    실험군 A (정상 로깅)  - 실험군 B (disabled)   = 순수 I/O 오버헤드
    실험군 B (disabled) - 실험군 C (NullLogger) = 함수 호출/객체 생성 오버헤드

주의:
    이 로거를 사용하면 어떠한 이벤트도 기록되지 않는다.
    실험 목적 외의 실제 실험 run에 절대 사용하지 말 것.
"""


class NullLogger:
    """모든 메서드 호출을 즉시 흡수하는 no-op 로거."""

    def __getattr__(self, name):
        """존재하지 않는 속성 접근 시 no-op 함수를 반환한다."""
        return lambda *args, **kwargs: None

    def log_event(self, event):
        return None

    def task_received(self, *args, **kwargs):
        return None

    def task_completed(self, *args, **kwargs):
        return None

    def inference_start(self, *args, **kwargs):
        return None

    def inference_end(self, *args, **kwargs):
        return None

    def queued(self, *args, **kwargs):
        return None

    def dequeued(self, *args, **kwargs):
        return None

    def dispatch_start(self, *args, **kwargs):
        return None

    def dispatch_end(self, *args, **kwargs):
        return None

    def execution_start(self, *args, **kwargs):
        return None

    def execution_end(self, *args, **kwargs):
        return None

    def retry_start(self, *args, **kwargs):
        return None

    def retry_end(self, *args, **kwargs):
        return None

    def run_metadata(self, *args, **kwargs):
        return None

    def worker_crash(self, *args, **kwargs):
        return None

    def queue_stall(self, *args, **kwargs):
        return None

    def retry_attempt(self, *args, **kwargs):
        return None

    def timeout_hit(self, *args, **kwargs):
        return None

    def api_429_error(self, *args, **kwargs):
        return None

    def profiling(self, *args, **kwargs):
        return None

    def worker_state(self, *args, **kwargs):
        return None
