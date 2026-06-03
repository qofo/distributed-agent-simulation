# LLM 기반 멀티 에이전트 시스템을 위한 분산 아키텍처 대규모 시뮬레이션 및 결함 내성 분석
**Comparative Simulation of Distributed Architectures for LLM-based Multi-Agent Systems: Scalability and Fault Tolerance**

---

## 1. 서론 (Introduction)

대규모 언어 모델(LLM)을 활용한 복합 추론 작업이 증가함에 따라, 다수의 에이전트(Agent)가 협업하여 문제를 해결하는 멀티 에이전트 분산 처리 시스템이 필수적으로 요구되고 있다. 
기존의 순차적(Monolithic) 접근 방식은 병목 현상과 심각한 지연 시간(Latency) 문제를 야기한다. 본 연구는 다양한 워크로드 특성(독립 병렬성 vs 순차 의존성)과 대규모 스케일링(최대 32개 워커) 상황에서 각 분산 아키텍처가 보여주는 처리량(Throughput), 지연 시간(Latency), 통신 오버헤드를 정량적으로 측정한다. 특히, 분산 환경의 핵심 요소인 꼬리 지연(Tail Latency, Straggler) 및 노드 중단(Crash) 발생 시 시스템의 **복원력(Resilience)과 단일 실패 지점(SPOF) 대응 능력**을 집중적으로 분석한다.

## 2. 실험 환경 및 시스템 아키텍처 (Experimental Setup)

네트워크와 추론 변수를 철저히 통제하기 위해, 고정 지연 시간(50~100ms)을 제공하는 Mock LLM 서버를 활용한 시뮬레이터에서 실험을 수행했다. **특히 이번 연구에서는 최대 32개의 워커(Worker) 노드를 동원하는 대규모 벤치마크 환경을 구축**하여 오버헤드 한계(Asymptote)를 확인했다.

### 2.1 4대 분산 아키텍처 설계
1. **Monolithic (모놀리식)**: 단일 스레드/프로세스 내에서 순차 처리. 기준점(Baseline) 역할.
2. **Master-Worker (마스터-워커)**: 중앙 마스터(Orchestrator)가 다수의 워커 스레드에 작업을 직접 디스패치하는 구조.
3. **Queue-Based (큐 기반)**: 중앙 메시지 브로커(Message Queue)를 통해 태스크를 퍼블리시하고 워커들이 자율적으로 폴링(Polling)하는 느슨한 결합.
4. **Swarm (스웜/P2P)**: 중앙 통제 없이, 에이전트 간 정적 라우팅에 따라 서로 직접 메시지를 핸드오프(Handoff)하는 탈중앙화 망 구조.

### 2.2 워크로드 모델링
* **Task A (Map-Reduce)**: 문서를 다수의 청크(Chunk=10)로 분할하여 독립적으로 처리 후 집계하는 극대화된 병렬 태스크.
* **Task B (Multi-hop QA)**: 이전 단계의 추론 결과가 다음 단계의 입력이 되는 연쇄적인 순차 의존 태스크.

---

## 3. 실험 결과 및 분석 (Evaluation & Analysis)

총 25개의 세부 튜닝된 환경(다양한 워커 수 및 장애 시나리오)에 대해 각 3회의 앙상블 테스트(Iteration)를 수행했다.

### 3.1 독립 병렬 워크로드 (Task A) 확장성 분석

병렬 처리가 극대화되는 Task A 환경에서 워커 수(W)를 4, 16, 32개로 늘려가며 스케일 업(Scale-up) 성능을 측정했다.

| Architecture | Throughput (Req/sec) | P50 Latency (sec) | Queue Wait (sec) |
| :--- | ---: | ---: | ---: |
| **Monolithic (W=1)** | 4.57 | 1.270 | 0.000 |
| **Master-Worker (W=4)** | 7.73 | 0.326 | 0.122 |
| **Master-Worker (W=32)** | 9.79 | 0.078 | 0.001 |
| **Queue-Based (W=4)** | 7.39 | 0.418 | 0.119 |
| **Queue-Based (W=32)** | 8.71 | 0.183 | 0.000 |
| **Swarm (W=4)** | 9.81 | **0.078** | 0.000 |
| **Swarm (W=32)** | **9.77** | **0.080** | 0.000 |

**분석 포인트 1: Swarm의 압도적 효율성**
Swarm 아키텍처는 에이전트 간 직접 핸드오프로 인해 중앙 병목이 없어, W=4의 적은 워커로도 이미 시스템 한계 처리량(약 9.8 Req/sec)에 도달하며 0.078초의 최단 지연 시간을 달성했다.
반면 Master-Worker와 Queue-Based는 워커가 32개까지 늘어난 후에야 Swarm의 초기 성능에 근접했다. 대규모 스레딩 오버헤드와 큐잉/디큐잉 락(Lock) 경합으로 인해 Queue-Based(W=32)는 여전히 0.18초의 지연 시간을 보였다.

> **그래프 참조**: [Throughput Chart (report2/throughput.png)](file:///c:/Users/BRAIN/Desktop/distributed-agent-simulation/report2/throughput.png)
> **그래프 참조**: [Latency Chart (report2/latency.png)](file:///c:/Users/BRAIN/Desktop/distributed-agent-simulation/report2/latency.png)

---

### 3.2 순차 의존성 워크로드 (Task B) 통신 오버헤드 분석

각 에이전트의 출력이 다음 에이전트의 입력으로 묶여 있어 병렬화가 불가능한 Task B(Multi-hop)의 결과이다.

| Architecture (W=2) | Throughput (Req/sec) | P50 Latency (sec) | 통신/큐 대기 시간 |
| :--- | ---: | ---: | ---: |
| Monolithic (W=1) | 6.86 | 0.532 | 0.000 |
| Master-Worker | 6.62 | 0.560 | 0.000 |
| **Queue-Based** | **6.27** | **0.644** | **누적 증가** |
| Swarm | 6.67 | 0.549 | 0.000 |

**분석 포인트 2: 메시지 큐의 태생적 딜레이**
작업이 순차적으로 이루어짐에 따라, 큐 기반 구조는 "결과 반환 -> 큐잉 -> 디큐잉 -> 다음 워커 실행"의 오버헤드를 모든 Step에서 반복해서 겪는다. 이로 인해 큐 기반 구조만 유일하게 Monolithic 보다 지연 시간이 20% 가까이 증가했다.

> **그래프 참조**: [Overhead Chart (report2/overhead_task_b.png)](file:///c:/Users/BRAIN/Desktop/distributed-agent-simulation/report2/overhead_task_b.png)

---

## 4. 장애 내성 및 복원력 (Failure Injection Model)

### 4.1 꼬리 지연 (Straggler) 효과와 로드 밸런싱
특정 노드에 고의적으로 500ms의 네트워크 딜레이를 발생시킨 결과:
* **Task A (병렬)**: Queue-Based 구조는 Straggler(500ms) 발생 시 전체 지연이 `0.67초`로 억제되었다. 큐를 통한 자연스러운 **로드 밸런싱(Idle 노드가 작업을 먼저 채감)** 덕분에 느린 노드의 악영향이 분산되었음을 증명한다. 지연을 `1000ms`로 극단적으로 늘렸을 때도 지연은 `1.16초`에 불과했다.
* **Task B (순차)**: 순차적 파이프라인에서 Straggler를 만나면 전체 시스템이 병목에 걸리며 Master-Worker 및 Queue-Based 모두 `2.0초`대까지 지연이 크게 폭증(Tail Latency Amplification)했다.

### 4.2 SPOF 및 노드 중단 (Crash Resilience) 메커니즘
무작위 워커 및 마스터 노드에 Crash 주입 시뮬레이션을 수행했다.

| Architecture | Crash 주입 시 평균 P50 Latency (sec) | 시스템 교착(Deadlock) 여부 |
| :--- | :--- | :--- |
| **Master-Worker** | 0.081 | 안전 (부분 결함 시 스킵 / 마스터 장애 시 즉시 실패) |
| **Queue-Based (개선 전)** | 34.00+ | **무한 루프(Infinite Re-queue) 및 시스템 마비** |
| **Queue-Based (개선 후)** | **2.580** | **Dead Letter Queue Timeout 후 복원 완료** |

**분석 포인트 3: 큐 기반 구조의 치명적 결함과 복원(Resilience)**
초기 Queue-Based 구조에서는 워커가 예외로 인해 죽을 시 잃어버린 작업을 오케스트레이터가 회수하지 못하거나 무한 루프(Infinite Loop)에 빠져 시스템 전체가 먹통이 되는 치명적인 결함이 존재했다. 
이를 2.0초의 타임아웃 감지 및 **안전한 태스크 ID 기반 Re-queue 메커니즘**으로 개선한 결과, 장애 발생 시 정확히 `2.58초(Timeout 대기 2초 + 재처리 0.5초)` 만에 살아남은 다른 워커들이 작업을 성공적으로 인수하여 시스템을 정상 복구해 내는 뛰어난 복원력(Resilience)을 증명하였다.

---

## 5. 결론 (Conclusion)

본 시뮬레이션은 LLM 멀티 에이전트 환경에서 각 아키텍처의 강점과 약점을 명확히 보여준다.
1. **극강의 성능과 오버헤드 최소화**: 중앙 관제에 얽매이지 않는 **Swarm(P2P) 구조**가 압도적으로 높은 성능을 보인다.
2. **높은 유연성과 내결함성**: **Queue-Based 아키텍처**는 타임아웃 및 재시도(Retry) 설계가 잘 갖춰져 있다면 Straggler 억제와 크래시 자동 복구(Auto-healing)에 가장 이상적인 구조이다.
3. **순차 작업의 주의점**: 의존성이 강한 Chain 형태의 워크로드에서는 잦은 큐잉과 네트워크 통신 오버헤드를 극도로 경계해야 한다.

향후 연구에서는 정적 라우팅을 넘어선 동적 디스커버리(Dynamic Discovery)를 적용한 Swarm 아키텍처 고도화를 진행할 예정이다.

---
**[AI Collaboration Note]**
본 논문의 설계, 결함 분석(Bug Tracking), 그리고 대규모 분산 오버헤드 픽스는 Gemini Advanced와의 고도의 Pair-Programming을 통해 작성 및 검증되었음을 명시한다.
