import time
import threading
from typing import Dict, Any, List
from core.config import GlobalConfig
from core.logger import StructuredLogger
from core.log_schema import LogEvent, EventType
from core.failure_injection import get_effective_latency, check_crash
from workloads.task_a import TaskAAdapter
from workloads.task_b import TaskBAdapter


def _build_routing_table(worker_count: int, total_steps: int) -> Dict[int, str]:
    """
    정적 라우팅 테이블 생성.
    각 step을 라운드로빈 방식으로 에이전트에 배정한다.
    중앙 오케스트레이터 없이 에이전트가 직접 다음 에이전트에게 핸드오프한다.
    """
    table = {}
    for step in range(total_steps):
        table[step] = f"swarm-agent-{(step % worker_count) + 1}"
    return table


def _agent_process_task_a(chunk, adapter, config, logger, run_id, trace_id, agent_id):
    """Swarm 에이전트가 Task A의 개별 청크를 처리한다."""
    chunk_task_id = f"{run_id}-{chunk['chunk_id']}"
    latency_sec = get_effective_latency(config, agent_id)

    logger.dequeued(trace_id, "swarm", chunk_task_id, agent_id)

    # Crash check
    check_crash(config, agent_id, logger, trace_id, "swarm", chunk_task_id)

    logger.inference_start(trace_id, "swarm", chunk_task_id, agent_id)

    logger.execution_start(trace_id, "swarm", chunk_task_id, agent_id, "mock")
    if latency_sec > 0:
        time.sleep(latency_sec)
    logger.execution_end(trace_id, "swarm", chunk_task_id, agent_id, "mock", int(latency_sec * 1000))

    context = {"logger": logger, "trace_id": trace_id, "architecture": "swarm", "worker_id": agent_id}
    res = adapter.process_chunk(chunk, context=context)

    logger.inference_end(trace_id, "swarm", chunk_task_id, agent_id, config.simulation.mock_inference_latency_ms)
    return res


def execute(config: GlobalConfig, logger: StructuredLogger, run_id: str, trace_id: str):
    """
    Swarm 아키텍처 실행기.
    중앙 마스터 없이 정적 라우팅 테이블에 따라 에이전트 간 직접 핸드오프를 수행한다.
    """
    task_type = config.experiment.task_type
    worker_count = config.experiment.worker_count

    if task_type == "A":
        # Task A: 각 에이전트가 독립적으로 청크를 처리 (P2P 방식으로 분배)
        adapter = TaskAAdapter(chunk_count=config.workload.chunk_count)
        chunks = adapter.split("dummy_input_data")
        routing_table = _build_routing_table(worker_count, len(chunks))

        # 첫 번째 에이전트가 작업을 수신하고 라우팅 테이블에 따라 분배
        initiator_id = routing_table[0]
        logger.log_event(LogEvent(
            trace_id=trace_id, architecture="swarm",
            task_id="swarm-init", event_type=EventType.TASK_RECEIVED,
            worker_id=initiator_id
        ))

        # 에이전트들이 병렬로 청크를 처리
        results = [None] * len(chunks)
        threads = []

        def worker_fn(idx, chunk):
            agent_id = routing_table[idx]
            try:
                return _agent_process_task_a(chunk, adapter, config, logger, run_id, trace_id, agent_id)
            except CrashSimulationError as e:
                raise e

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = []
            for i, chunk in enumerate(chunks):
                chunk_task_id = f"{run_id}-{chunk['chunk_id']}"
                agent_id = routing_table[i]

                # 이전 에이전트가 다음 에이전트에게 핸드오프 로그
                if i > 0:
                    prev_agent = routing_table[i - 1]
                    logger.dispatch_start(trace_id, "swarm", f"handoff-chunk-{i}", prev_agent, "swarm_route")
                    logger.log_event(LogEvent(
                        trace_id=trace_id, architecture="swarm",
                        task_id=f"handoff-chunk-{i}",
                        event_type=EventType.HANDOFF,
                        worker_id=prev_agent,
                        details={"target_agent": agent_id}
                    ))
                    logger.dispatch_end(trace_id, "swarm", f"handoff-chunk-{i}", prev_agent, "swarm_route")

                logger.queued(trace_id, "swarm", chunk_task_id)
                logger.dispatch_start(trace_id, "swarm", chunk_task_id, initiator_id, "swarm_route")
                futures.append(executor.submit(worker_fn, i, chunk))
                logger.dispatch_end(trace_id, "swarm", chunk_task_id, initiator_id, "swarm_route")

            # 결과를 순서대로 취합 (Crash 발생 시 예외 발생으로 Request 전체 실패)
            for i, future in enumerate(futures):
                try:
                    results[i] = future.result()
                except CrashSimulationError as e:
                    raise e

        # Aggregation: 마지막 에이전트가 수행
        last_agent = routing_table[len(chunks) - 1]
        logger.log_event(LogEvent(
            trace_id=trace_id, architecture="swarm",
            task_id="aggregation", event_type=EventType.AGGREGATION_START,
            worker_id=last_agent
        ))
        valid_results = [r for r in results if r is not None]
        final_result = adapter.aggregate(valid_results)
        logger.log_event(LogEvent(
            trace_id=trace_id, architecture="swarm",
            task_id="aggregation", event_type=EventType.AGGREGATION_END,
            worker_id=last_agent
        ))

    elif task_type == "B":
        # Task B: 순차 핸드오프 (에이전트 간 직접 전달)
        adapter = TaskBAdapter(total_steps=config.workload.chunk_count)
        state = adapter.create_initial_state("dummy_query")
        routing_table = _build_routing_table(worker_count, config.workload.chunk_count)

        current_agent = routing_table[0]
        logger.log_event(LogEvent(
            trace_id=trace_id, architecture="swarm",
            task_id="swarm-init", event_type=EventType.TASK_RECEIVED,
            worker_id=current_agent
        ))

        step_counter = 0
        while not state["is_complete"]:
            current_agent = routing_table.get(step_counter, f"swarm-agent-{(step_counter % worker_count) + 1}")
            step_task_id = f"{run_id}-step-{state['current_step']}"
            latency_sec = get_effective_latency(config, current_agent)

            logger.dequeued(trace_id, "swarm", step_task_id, current_agent)

            # Crash check
            check_crash(config, current_agent, logger, trace_id, "swarm", step_task_id)

            logger.inference_start(trace_id, "swarm", step_task_id, current_agent)

            logger.execution_start(trace_id, "swarm", step_task_id, current_agent, "mock")
            if latency_sec > 0:
                time.sleep(latency_sec)
            logger.execution_end(trace_id, "swarm", step_task_id, current_agent, "mock", int(latency_sec * 1000))

            context = {"logger": logger, "trace_id": trace_id, "architecture": "swarm", "worker_id": current_agent}
            state = adapter.process_step(state, context=context)

            logger.inference_end(trace_id, "swarm", step_task_id, current_agent, config.simulation.mock_inference_latency_ms)

            # 핸드오프 로그 (다음 에이전트에게 직접 전달)
            if not state["is_complete"]:
                next_agent = routing_table.get(step_counter + 1, f"swarm-agent-{((step_counter + 1) % worker_count) + 1}")
                logger.dispatch_start(trace_id, "swarm", f"handoff-{state['current_step']}", current_agent, "swarm_route")
                logger.log_event(LogEvent(
                    trace_id=trace_id, architecture="swarm",
                    task_id=f"handoff-{state['current_step']}",
                    event_type=EventType.HANDOFF,
                    worker_id=current_agent,
                    details={"target_agent": next_agent}
                ))
                logger.dispatch_end(trace_id, "swarm", f"handoff-{state['current_step']}", current_agent, "swarm_route")

            step_counter += 1

    else:
        raise ValueError(f"Unknown task_type: {task_type}")
