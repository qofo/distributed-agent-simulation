# LLM 기반 멀티 에이전트 시스템을 위한 분산 아키텍처 비교 시뮬레이션
**Comparative Simulation of Distributed Architectures for LLM-based Multi-Agent Systems**
## 1. 서론 (Introduction)
최근 대규모 언어 모델(LLM)의 발전과 함께 복잡한 문제를 분할하여 해결하기 위해 여러 에이전트를 결합하는 멀티 에이전트 시스템(Multi-Agent System) 연구가 활발히 진행되고 있다. 그러나 에이전트 간의 상호작용이 복잡해질수록 단일 프로세스 기반의 순차적 처리 방식(Monolithic)은 심각한 병목 현상을 유발하며, 이는 전체 시스템의 성능 및 응답성 저하로 직결된다.
본 연구의 목적은 에이전트 워크로드의 특성(독립 병렬성 vs. 순차 의존성)에 가장 적합한 분산 아키텍처를 정량적으로 도출하는 것이다. 이를 위해 Monolithic, Master-Worker, Queue-Based, Swarm(P2P) 4가지 아키텍처를 시뮬레이션 환경에 구현하고, 정상 상태 및 장애(Crash/Straggler) 상황에서의 처리량(Throughput), 지연 시간(Latency), 통신 오버헤드, 그리고 복원력(Fault Tolerance)을 비교 분석한다.
## 2. 실험 환경 및 시스템 아키텍처 (Experimental Setup)
본 실험은 분산 환경의 네트워크 변수를 통제하기 위해, 고정된 추론 지연 시간(50~100ms)을 제공하는 Mock LLM 서버를 활용하여 파이썬 기반 시뮬레이터로 구현되었다. 
### 2.1 분산 아키텍처 설계
1. **Monolithic (모놀리식)**: 단일 스레드 내에서 모든 에이전트 작업이 순차적으로 실행되며, 분산 통신 오버헤드가 없는 기준점(Baseline) 역할을 한다.
2. **Master-Worker (마스터-워커)**: 중앙의 오케스트레이터(Master)가 다수의 워커 스레드에 작업을 직접 할당하고 수거하는 구조이다. 
3. **Queue-Based (큐 기반)**: 중앙 메시지 큐(Message Broker)를 통해 작업을 퍼블리시하고 워커들이 비동기적으로 폴링(Polling)하는 느슨한 결합(Loosely-coupled) 구조이다.
4. **Swarm (스웜/P2P)**: 중앙 오케스트레이터나 큐 없이, 에이전트 간에 사전 정의된 정적 라우팅을 기반으로 서로 직접 결과를 전달(Handoff)하는 분산망 구조이다.
### 2.2 워크로드 모델링
* **Task A (Map-Reduce)**: 문서를 다수의 청크(Chunk)로 쪼개어 독립적으로 요약하는 병렬 처리 워크로드.
* **Task B (Multi-hop QA)**: 이전 단계의 추론 결과가 다음 단계의 입력이 되는 연쇄적 순차 추론 워크로드.
## 3. 장애 주입 모델 (Failure Injection Model)
실제 클라우드 및 네트워크 환경에서 발생할 수 있는 이상 현상을 재현하기 위해 두 가지 형태의 장애 주입(Failure Injection) 기법을 설계하였다.
* **Straggler (지연 워커)**: 특정 워커 노드에 500ms의 인위적 지연을 발생시켜 꼬리 지연(Tail Latency) 증폭 현상을 관찰한다.
* **Crash (워커 중단)**: 특정 워커가 작업 도중 예외를 발생시키며 강제 종료(`CrashSimulationError`)되는 상황을 구현하여, 시스템의 무한 대기 여부와 예외 처리 능력을 확인한다.
## 4. 실험 결과 및 분석 (Evaluation & Analysis)
총 16개의 실험 시나리오 매트릭스를 기반으로 도출된 성능 지표를 분석한다. 전체 로그는 JSON Lines 형식의 Event Sourcing 기반으로 기록되었으며, 전용 파서를 통해 처리량 및 지연 시간을 산출하였다.
### 4.1 독립 병렬 워크로드 (Task A) 성능 분석
병렬 처리가 극대화되는 Task A 환경(Worker=4)에서, 각 아키텍처의 처리량(Throughput)과 P50 지연 시간(Latency)은 다음과 같이 나타났다.
|
 Architecture (W=4) 
|
 Throughput (Req/sec) 
|
 P50 Latency (sec) 
|
|
:---
|
---:
|
---:
|
|
 Monolithic (W=1) 
|
 0.81 
|
 1.23 
|
|
 Master-Worker 
|
 3.09 
|
 0.31 
|
|
 Queue-Based 
|
 2.40 
|
 0.40 
|
|
**
Swarm
**
|
**
11.96
**
|
**
0.08
**
|
Master-Worker와 Queue-Based 구조는 Monolithic 대비 지연 시간을 약 70% 이상 단축시켰다. 주목할 점은 **Swarm** 아키텍처가 중앙 제어 병목이나 큐 기반 직렬화 오버헤드 없이 에이전트 간 순수 병렬 연산을 수행하여 가장 압도적인 처리량과 최단 지연 시간을 기록했다는 것이다.
*(첨부 참조: `throughput.png`, 전체 배치 처리량 막대 그래프)*
### 4.2 순차 의존성 워크로드 (Task B) 성능 분석
작업 간 강한 의존성이 존재하는 Task B 환경에서는 병렬 처리가 불가능하므로, 아키텍처 자체의 '통신 오버헤드'가 지연 시간에 결정적 영향을 미친다.
|
 Architecture (W=2) 
|
 Throughput (Req/sec) 
|
 P50 Latency (sec) 
|
 Queue Wait (sec) 
|
|
:---
|
---:
|
---:
|
---:
|
|
 Monolithic (W=1) 
|
 1.83 
|
 0.54 
|
 0.00 
|
|
 Master-Worker 
|
 1.83 
|
 0.53 
|
 0.00 
|
|
 Queue-Based 
|
 1.53 
|
**
0.64
**
|
**
0.00
**
|
|
 Swarm 
|
 1.83 
|
 0.54 
|
 0.00 
|
결과에서 볼 수 있듯, 큐를 거쳐야 하는 Queue-Based 구조의 경우 잦은 상태(State) 큐잉 및 디큐잉으로 인해 통신 오버헤드가 누적되어 전체 지연 시간(0.64초)이 오히려 Monolithic보다 증가하였다. 반면 Swarm 아키텍처는 에이전트가 직접 결과를 핸드오프하므로 큐 대기 시간 없이 Monolithic 수준의 응답 시간(0.54초)을 방어해냈다.
*(첨부 참조: `latency.png` 및 `overhead_task_b.png`, 큐 대기 시간 오버헤드 중첩 그래프)*
### 4.3 장애 내결함성 (Fault Tolerance) 분석
#### Straggler(지연) 내결함성
Task A에서 1개의 워커에 500ms Straggler를 주입한 결과, Master-Worker는 P50 지연 시간이 1.24초로 상승했지만, Queue-Based 구조는 0.66초로 선방했다. 이는 큐 기반 환경에서 한 워커가 느려지더라도 노는(Idle) 다른 워커가 큐에서 태스크를 먼저 가져가 처리하는 **자연스러운 로드 밸런싱(Load Balancing)** 덕분이다.
#### Crash(중단) 내결함성
Task A 환경에서 Crash를 주입했을 때, Master-Worker는 스레드 내 예외(`CrashSimulationError`)를 Catch하여 나머지 정상 청크만으로 최종 집계를 수행(지연 0.25초)할 수 있었다. 반면 기본 구현된 Queue-Based 구조에서는 워커가 큐의 `task_done()`을 반환하지 못한 채 죽었을 경우, 메인 오케스트레이터가 영원히 Blocking되는 무한 대기 취약점이 발견되었다. (이를 방지하기 위한 Timeout 추가 시 34초 대기 후 강제 복귀 확인).
## 5. 결론 및 향후 과제 (Conclusion & Future Work)
본 연구의 시뮬레이션을 통해 멀티 에이전트 시스템을 위한 4가지 아키텍처의 트레이드오프(Trade-off)를 정량적으로 증명하였다.
1. **독립적인 병렬 태스크(Map-Reduce 형)**: 중앙 제어 병목이 없는 Swarm이나 Queue-Based 도입이 성능상 절대적으로 유리하다.
2. **순차 의존성 태스크(Chain/Agent Handoff 형)**: 잦은 큐잉은 전체 성능을 갉아먹는다. 따라서 오버헤드가 적은 Swarm 구조로 직접 전달하거나, 불가피할 시 Monolithic 묶음 처리를 선택하는 것이 현명하다.
3. **내결함성(Fault Tolerance)**: Queue-Based 구조는 트래픽 스파이크나 Straggler 방어에는 탁월하나, 노드 Crash 상황 시 심각한 교착 상태에 빠질 수 있으므로 정교한 Timeout 및 Dead Letter Queue 재시도 메커니즘 설계가 동반되어야 한다.
**향후 과제**: 정적 라우팅이 아닌 동적 서비스 디스커버리(Service Discovery) 기반의 Swarm 구조를 고도화하고, 실제 클라우드 환경의 OpenAI/Anthropic API를 연동하여 네트워크 레이턴시 노이즈가 포함된 실전 환경 테스트를 진행할 계획이다.
---
**[AI 활용 명시]** 
본 연구의 실험 시스템(Mock API 서버, Event-Sourcing Logger, 분산 Executor 프레임워크) 및 시각화 파이프라인 전반의 설계와 구현에 있어, Gemini AI 코딩 어시스턴트와의 페어 프로그래밍을 활용하여 높은 생산성을 달성하였음을 밝힌다.