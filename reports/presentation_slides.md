# 분산 에이전트 시뮬레이션 발표 자료 (3분)

## Slide 1: Title
**제목:** LLM 기반 멀티 에이전트 시스템을 위한 분산 아키텍처 비교 시뮬레이션
**부제:** Monolithic, Master-Worker, Queue-Based 아키텍처 성능 분석
**발표자:** [이름/학번 기입]

---

## Slide 2: Overview & Objective (개요 및 목표)
- **배경:** 대규모 LLM 에이전트 작업 시 단일 프로세스의 병목 현상 발생.
- **목표:** 서로 다른 세 가지 아키텍처를 구현하고, 워크로드 특성(독립형 분할 vs 순차적 체인)에 따른 성능(처리량, 지연 시간)을 실험적으로 비교.
- **의의:** 복잡한 에이전트 시스템을 설계할 때 가장 효율적인 분산 처리 구조를 선택하기 위한 정량적 가이드라인 제시.

---

## Slide 3: Architectures (구현 아키텍처)
1. **Monolithic (기준점):** 모든 작업을 단일 프로세스에서 순차적으로 처리.
2. **Master-Worker (중앙 집중형):** 중앙 오케스트레이터가 작업을 나누어 다수의 워커 스레드(Worker Threads)에 직접 할당 및 회수.
3. **Queue-Based (비동기 큐 기반):** 메시지 브로커(큐)를 통해 생성자와 소비자를 완전히 분리한 느슨한 결합(Loosely-coupled) 구조.

---

## Slide 4: Workloads (실험 워크로드)
- **Task A (Map-Reduce):** 문서를 여러 청크(Chunk)로 쪼개어 독립적으로 요약한 뒤 병합. (병렬 처리 극대화 테스트)
- **Task B (Multi-hop QA):** 이전 단계의 결과가 다음 단계의 입력이 되는 순차적 추론. (작업 간 의존성과 Handoff 오버헤드 테스트)
- **통제 변인:** Mock LLM을 사용하여 추론 지연 시간(Latency)을 고정(50ms~100ms)하여 외부 네트워크 변수를 통제.

---

## Slide 5: Results - Task A (독립형 병렬 작업)
- **처리량(Throughput):** 워커 수(Worker Count)에 비례하여 선형적으로 증가.
- **비교:** Master-Worker와 Queue-Based 모두 Monolithic 대비 압도적인 성능 향상.
- **결과 이미지:** `throughput.png` 차트 삽입

---

## Slide 6: Results - Task B (순차적 체인 작업)
- **지연 시간(Latency):** 작업 간 의존성으로 인해 워커 수를 늘려도 전체 소요 시간은 줄어들지 않음.
- **큐 오버헤드:** Queue-Based 구조의 경우 잦은 상태 직렬화/역직렬화 및 큐 대기 시간(Queue Wait Time)으로 인해 오히려 미세한 지연 시간 증가 확인.
- **결과 이미지:** `latency.png` 차트 삽입

---

## Slide 7: Conclusion (결론 및 AI 활용)
- **결론:** 
  - 서로 독립적인 대량의 에이전트 작업(Task A)에는 Queue나 Master-Worker를 통한 병렬화가 필수적.
  - 하지만 순차적이고 결합도가 높은 추론(Task B)에서는 잦은 분산 통신 오버헤드가 배보다 배꼽이 더 커질 수 있으므로 Monolithic에 가까운 묶음 처리가 유리.
- **AI 활용 명시:** 본 프로젝트의 초기 아키텍처 설계, Mock LLM API 구현 및 파이썬 분산 시뮬레이션 프레임워크 작성 시 Gemini 기반 AI 코딩 어시스턴트의 지원을 받아 개발 효율성을 극대화함.
- **Q&A:** 감사합니다.
