# 분산 에이전트 시뮬레이션 발표 자료 (3분)

## Slide 1: Title
**제목:** LLM 기반 멀티 에이전트 시스템을 위한 분산 아키텍처 비교 시뮬레이션
**부제:** Monolithic, Master-Worker, Queue-Based, Swarm 아키텍처 성능 분석
**발표자:** [이름/학번 기입]

---

## Slide 2: Overview & Objective (개요 및 목표)
- **배경:** 대규모 LLM 에이전트 작업 시 단일 프로세스의 병목 현상 발생 및 부분 장애의 위험성 존재.
- **목표:** 서로 다른 4가지 아키텍처를 구현하고, 워크로드 특성(독립형 분할 vs 순차적 체인)과 장애 상황(Crash/Straggler)에 따른 성능(처리량, 지연 시간, 장애 복원력)을 실험적으로 비교.
- **의의:** 복잡한 에이전트 시스템을 설계할 때 가장 효율적이고 안정적인 분산 처리 구조를 선택하기 위한 정량적 가이드라인 제시.

---

## Slide 3: Architectures (구현 아키텍처)
1. **Monolithic:** 모든 작업을 단일 프로세스에서 순차적으로 처리. (기준점)
2. **Master-Worker:** 중앙 오케스트레이터가 워커 스레드에 직접 할당. (중앙 집중형)
3. **Queue-Based:** 메시지 큐를 통해 생산자와 소비자를 완전히 분리. (느슨한 결합)
4. **Swarm (P2P):** 정적 라우팅을 기반으로 에이전트들이 중앙 제어 없이 직접 핸드오프. (분산형)

---

## Slide 4: Workloads & Failure Injection (실험 환경)
- **Task A (Map-Reduce):** 문서를 여러 청크(Chunk)로 쪼개어 독립적으로 병렬 요약.
- **Task B (Multi-hop QA):** 이전 단계의 결과가 다음 단계의 입력이 되는 순차적 추론 체인.
- **장애 주입 (Failure Injection):** 실제 운영 환경과 유사하도록 특정 워커의 지연(Straggler) 및 완전 중단(Crash) 상황을 시뮬레이션에 통합.

---

## Slide 5: Results - Task A & Task B 기본 성능
- **Task A (병렬):** Master-Worker와 Queue-Based는 워커 수에 비례하여 처리량이 증가하지만, Swarm 아키텍처가 중앙 제어 오버헤드가 없어 가장 높은 처리량을 기록.
- **Task B (순차 체인):** 워커를 늘려도 순차 처리로 인해 전체 소요 시간은 줄어들지 않음. 오히려 Queue-Based 구조는 큐 대기 시간(Queue Wait Time)으로 인해 지연 시간이 다소 증가. Swarm은 직접 핸드오프를 통해 Monolithic 수준의 빠른 지연 시간을 유지.
- **결과 이미지:** `throughput.png`, `latency.png`, `overhead_task_b.png` 차트 참조

---

## Slide 6: Results - Failure Injection (장애 내결함성)
- **Straggler (느린 워커):** 일부 워커가 느려지는 꼬리 지연(Tail Latency) 상황에서 Queue-Based 아키텍처는 놀고 있는 다른 워커가 작업을 대신 가져가므로 전체 시스템 지연 방어에 가장 효과적임.
- **Crash (워커 중단):** Master-Worker는 Crash 예외를 포착하여 다른 청크 작업을 지속할 수 있으나, 단순 Queue-Based(Timeout 미적용 시)는 큐의 메시지를 반환받지 못해 무한 대기에 빠질 수 있는 취약점을 발견.

---

## Slide 7: Conclusion (결론 및 AI 활용)
- **결론:** 
  - 서로 독립적이고 대량인 에이전트 작업(Task A)에는 P2P(Swarm)나 중앙 집중 분산 처리가 유리.
  - 하지만 순차적 체인(Task B)에서는 잦은 큐 통신이 오버헤드를 유발하므로 P2P 직접 전달(Swarm)이 가장 이상적.
  - **운영 안정성:** 장애 변수가 많은 환경에서는 Queue-Based가 유연하지만 철저한 Timeout 및 재시도(Retry) 로직 설계가 필수.
- **AI 활용 명시:** 본 프로젝트의 초기 아키텍처 설계, Mock LLM 구현, 분산 시뮬레이션 프레임워크 작성 및 디버깅 시 Gemini 기반 AI 코딩 어시스턴트의 지원을 받아 완성도를 크게 높임.
- **Q&A:** 감사합니다.
