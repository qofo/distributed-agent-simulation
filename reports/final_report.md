# 실증적 분산 에이전트 아키텍처 비교 및 워크로드 병렬성 분석 보고서

## 1. Abstract & Introduction

본 보고서는 LLM 기반 분산 에이전트 시스템에서 흔히 사용되는 4가지 아키텍처 패턴(Monolithic, Master-Worker, Queue-Based, Swarm)의 성능 오버헤드와 장애 복원력(Resilience)을 실증적으로 비교 분석한다. 특히, 아키텍처 자체의 설계 차이보다 시스템이 처리해야 하는 **워크로드의 병렬성 한계**가 전체 성능에 미치는 지배적인 영향을 규명한다.

### 실험 목적 및 한계 (Known Limitations)
이 프로젝트는 상용 소프트웨어 제품이 아닌 통제된 실험 프레임워크다. 외부 네트워크 변수(실제 LLM 호출 지연, Redis 등 메시지 브로커 I/O)를 통제하기 위해 모든 지연 시간은 Mocking되었으며, 에이전트 간 통신은 인메모리로 처리되었다.
사전 검증(P1)을 통해 본 프레임워크의 계측 로깅 오버헤드가 전체 실행 시간의 1% 미만이며, 실험 변동계수(CV)가 10% 미만으로 매우 안정적인 재현성을 확보했음을 확인했다. (자세한 내용은 `known_limitations.md` 참조)

## 2. Baseline Results (정상 상태 성능 비교)

장애가 주입되지 않은 정상(Baseline) 상태에서의 아키텍처별 Wall-clock Time을 비교한다.

*TODO: Baseline 막대 그래프 삽입 (`results/final/plots/baseline_comparison.png`)*

**(분석 내용 요약 - 데이터 추출 완료 후 업데이트 예정)**
- 병렬 처리(Task A) 환경에서의 아키텍처 간 차이
- 순차 처리(Task B) 환경에서의 아키텍처 간 차이

## 3. Bottleneck Analysis (핵심 발견: 워크로드 병렬성)

본 실험의 가장 중요한 발견은, 아키텍처의 라우팅 효율성보다 워크로드의 병렬성이 전체 성능을 지배한다는 점이다.

*TODO: Worker Utilization 그래프 삽입 (`results/final/plots/utilization_task_A.png`, `results/final/plots/utilization_task_B.png`)*

### 3.1 라우팅 오버헤드의 무의미성
사전 분석 결과, Swarm 등 분산 구조에서 에이전트 간 작업 라우팅 및 핸드오프(Handoff)에 소요되는 시간은 전체 Wall-clock Time의 **0.1% ~ 0.6% 수준**에 불과했다. 즉, 라우팅 최적화(예: Load-Aware Routing)는 성능 개선에 기여하지 못한다.

### 3.2 제한적 동시성 (Concurrent Busy Agents)
활성 상태인 에이전트의 분포를 측정한 결과, Worker가 여러 대 존재함에도 불구하고 대부분의 시간 동안 **활성 에이전트는 1대**에 머물렀다.
- **Task A (병렬)**: 동기화(Aggregation) 및 할당 구조의 한계로 다수 에이전트가 동시에 작업하는 구간이 극히 짧음.
- **Task B (순차)**: 구조상 1개의 에이전트만 작업하므로 나머지 에이전트는 항상 대기.

이는 "아키텍처가 느리다"기보다는 "워크로드가 여러 에이전트를 동시에 바쁘게 만들지 못한다"는 실증적 증거다.

## 4. Resilience Analysis (장애 복원력)

시스템의 일부 컴포넌트에 장애(Crash) 또는 지연(Straggler)이 발생했을 때 아키텍처가 어떻게 반응하는지 관찰했다.

*TODO: Failure Impact 그래프 삽입 (`results/final/plots/failure_impact_task_A.png`, `results/final/plots/failure_impact_task_B.png`)*

### 4.1 Crash (프로세스 강제 종료)
- **Monolithic**: 즉시 전체 실패. 단일 장애점(SPOF).
- **Master-Worker / Queue-Based**: 중앙 통제 혹은 큐를 통한 자동 재시도로 복구 가능.
- **Swarm**: (데이터 추출 후 평가 업데이트)

### 4.2 Straggler (지연 발생)
- 특정 에이전트에 지연이 발생했을 때, 이것이 전체 완료 시간에 미치는 영향. 순차적 구조(Task B)에서는 이 지연이 그대로 전체 지연으로 이어지지만, 병렬 구조(Task A)에서는 큐 기반 구조가 동적 할당을 통해 지연을 어떻게 흡수하는지 관찰.
**(데이터 추출 후 평가 업데이트)**

## 5. Conclusion (결론 및 제언)

1. **라우팅 최적화의 함정**: 현재의 LLM 에이전트 워크로드(대부분 순차적이거나 동기화 지점이 많은 병렬 구조)에서는 복잡한 라우팅 아키텍처(Advanced Swarm 등)를 도입하는 것의 효용이 매우 낮다.
2. **단일/제한적 동시성 환경에서의 아키텍처 선택**: 
   - 높은 장애 복원력(Resilience)이 필요하다면 오버헤드를 감수하더라도 Queue-Based 구조가 가장 방어력이 높다.
   - 단순성이 최우선이고 치명적 장애 확률이 낮다면 Monolithic이나 Master-Worker 구조가 여전히 유효하다.
3. 아키텍처 설계자는 오케스트레이션 로직을 고도화하기 전에, **처리하려는 워크로드 자체가 실제로 분산 처리 가능한 형태인지(병렬화 가능성)**를 먼저 검증해야 한다.
