# 실증적 분산 에이전트 아키텍처 비교 및 워크로드 병렬성 분석 보고서

## 1. Abstract & Introduction

본 보고서는 LLM 기반 분산 에이전트 시스템에서 흔히 사용되는 4가지 아키텍처 패턴(Monolithic, Master-Worker, Queue-Based, Swarm)의 성능 오버헤드와 장애 복원력(Resilience)을 실증적으로 비교 분석한다. 특히, 아키텍처 자체의 설계 차이보다 시스템이 처리해야 하는 **워크로드의 병렬성 한계**가 전체 성능에 미치는 지배적인 영향을 규명한다.

### 실험 목적 및 한계 (Known Limitations)
이 프로젝트는 상용 소프트웨어 제품이 아닌 통제된 실험 프레임워크다. 외부 네트워크 변수(실제 LLM 호출 지연, Redis 등 메시지 브로커 I/O)를 통제하기 위해 모든 지연 시간은 Mocking되었으며, 에이전트 간 통신은 인메모리로 처리되었다.
사전 검증(P1)을 통해 본 프레임워크의 계측 로깅 오버헤드가 전체 실행 시간의 1% 미만이며, 실험 변동계수(CV)가 10% 미만으로 매우 안정적인 재현성을 확보했음을 확인했다. (자세한 내용은 `known_limitations.md` 참조)

## 2. Baseline Results (정상 상태 성능 비교)

장애가 주입되지 않은 정상(Baseline) 상태에서의 아키텍처별 Wall-clock Time을 비교한다.

*TODO: Baseline 막대 그래프 참조 (`results/final/plots/baseline_comparison.png`)*

## 2. Baseline Results (정상 상태 성능 비교)

장애가 주입되지 않은 정상(Baseline) 상태에서의 아키텍처별 Wall-clock Time을 비교한다.

*TODO: Baseline 막대 그래프 참조 (`results/final/plots/baseline_comparison.png`)*

- **병렬 처리(Task A)**: Swarm(6.5초)이 가장 빠르고 Master-Worker(7.2초), Queue-Based(8.3초)가 뒤를 이었다. 반면 Monolithic은 13.4초로 가장 느렸다.
- **순차 처리(Task B)**: Monolithic(61.8초), Master-Worker(63.0초), Swarm(67.5초) 모두 60초대의 비슷한 실행 시간을 기록했다. (주의: 초기 분석에서 Queue-Based가 32.8초로 측정되었으나, 검증 결과 이는 성능 우위가 아닌 오케스트레이터의 30초 Timeout 설정으로 인한 강제 조기 종료(측정 오류 및 실패)였음이 확인되었다.)

## 3. Bottleneck Analysis (핵심 발견: 워크로드 병렬성)

본 실험의 가장 중요한 발견은, 아키텍처의 라우팅 방식보다 워크로드의 병렬성이 전체 성능을 지배한다는 점이다.

*TODO: Worker Utilization 막대 그래프 참조 (`results/final/plots/utilization_task_A.png`, `results/final/plots/utilization_task_B.png`)*

### 3.1 라우팅 오버헤드의 무의미성
본 실험 환경에서는 분산 구조의 에이전트 간 작업 라우팅 및 핸드오프(Handoff)에 소요되는 시간은 전체 Wall-clock Time의 **0.1% ~ 0.6% 수준**으로 매우 작게 관측되었다. 따라서 현재 워크로드에서는 라우팅 최적화(예: Load-Aware Routing)가 전체 성능 개선에 미치는 영향이 제한적이었다.

### 3.2 제한적 동시성 (Concurrent Busy Agents)
활성 상태인 에이전트의 분포를 측정한 결과, Worker가 여러 대 존재함에도 불구하고 대부분의 시간 동안 **활성 에이전트는 1대**에 머물렀다.
데이터 집계 결과에 따르면, 다중 워커 아키텍처임에도 불구하고 **Idle(대기) 비중이 32%~66%** 로 높게 관측되었으며, 이는 워크로드 자체의 병렬성 부족 또는 동기화/큐 대기 시간 증가를 시사한다.
- **Task A (병렬)**: 동기화 구간 대기 등으로 인해 다수 에이전트가 동시에 일하는 구간이 제한적이다.
- **Task B (순차)**: 구조상 1대의 워커가 병목이 되므로 여러 에이전트를 동시에 바쁘게 만들지 못했다.

## 4. Resilience Analysis (장애 복원력)

시스템의 일부 컴포넌트에 장애(Crash) 또는 지연(Straggler, 500ms 추가지연)이 발생했을 때 아키텍처가 어떻게 반응하는지 관찰했다.

*TODO: Failure Impact 막대 그래프 참조 (`results/final/plots/failure_impact_task_A.png`, `results/final/plots/failure_impact_task_B.png`)*

### 4.1 Crash (프로세스 강제 종료)
- **Monolithic**: 단일 프로세스이므로 전체 지연이 발생하며 실패 타격이 컸다.
- **Master-Worker / Queue-Based**: 중앙 통제 혹은 큐를 통한 작업 재할당으로 장애를 흡수(Absorb)하는 복원력을 보였다.
- **Swarm**: 본 연구에서 구현한 Swarm 모델은 자체적인 재할당 및 복구 메커니즘이 포함되지 않아 Crash 상황 발생 시 치명적인 조기 실패(Failure)로 이어지며 취약했다.

### 4.2 Straggler (지연 발생)
- Master-Worker 및 Queue-Based 구조는 부분 지연이 발생해도 동적 할당의 장점을 통해 이를 흡수해 전체 지연으로 확산되는 것을 막았다. 반면 단일 워커 구조는 이를 그대로 짊어져 시간이 지연되었다.

## 5. Conclusion (결론 및 제언)

본 실험에서는 아키텍처 간 라우팅 방식보다 워크로드의 병렬성 수준이 전체 성능에 더 큰 영향을 미쳤다. 

특히 순차 의존성이 높은 작업에서는 워커 수 증가와 복잡한 분산 구조가 기대만큼의 성능 향상을 제공하지 못했다. 반면 장애 복원력 측면에서는 중앙 조정 또는 작업 재할당 메커니즘을 가진 구조가 더 안정적인 특성을 보였다.

따라서 분산 에이전트 시스템 설계 시 아키텍처 선택에 앞서 대상 워크로드가 실제로 병렬화 가능한지 평가하는 과정이 선행되어야 한다.
