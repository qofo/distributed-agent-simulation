# 인수인계 가이드 (Handover Guide)

이 문서는 `distributed-agent-simulation` 프로젝트에 처음 참여하시는 분들을 위해, 프로젝트의 전반적인 구조와 핵심 코드 동작 방식을 설명하기 위해 작성되었습니다.

---

## 1. 프로젝트 개요
이 프로젝트는 **LLM 기반 멀티 에이전트 아키텍처를 분산 시스템 관점에서 비교 평가**하기 위한 시뮬레이션 환경(Harness)입니다.
단순히 "어떤 프롬프트가 더 좋은 답변을 내는가?"가 아니라, **"Worker 수가 늘어날 때 선형 확장이 가능한가?", "장애나 지연(Straggler)이 발생했을 때 시스템이 어떻게 복구되는가?", "아키텍처별 병목 지점은 어디인가?"**를 측정하고 분석하는 것이 목표입니다.

---

## 2. 전체 디렉터리 구조

프로젝트의 핵심 디렉터리 구조는 다음과 같습니다:

```text
distributed-agent-simulation/
├── architectures/  # 4가지 서로 다른 멀티 에이전트 구조 구현체
├── core/           # 시스템 전반에서 공통으로 사용되는 핵심 모듈
├── workloads/      # 에이전트들이 수행할 작업(Task A, Task B) 정의
├── runner/         # 실험을 실행하는 스크립트 모음
├── parser/         # 생성된 로그를 파싱하여 메트릭(throughput, latency 등)을 추출하는 모듈
├── mock_llm/       # 실제 LLM 대신 레이턴시를 시뮬레이션하기 위한 Mock 서버
├── configs/        # 실험 파라미터가 정의된 설정 파일들
├── data/           # 실험에 사용될 dummy 데이터셋
├── logs/           # 실행 시 생성되는 Raw JSON Lines 로그
├── results/        # 로그를 파싱한 결과(CSV 등) 저장
└── reports/        # 최종 결과 요약 및 발표 자료 등
```

---

## 3. 핵심 모듈 설명

### `core/` (코어 모듈)
모든 아키텍처가 공통으로 의존하는 기반 시스템입니다.
* `config.py`: 실험 설정(워커 수, 아키텍처 타입, 장애 주입 등)을 관리합니다.
* `logger.py` & `log_schema.py`: 추적 가능한 JSON Lines 형태의 로그를 남깁니다. 각 요청마다 `trace_id`를 부여하여 분산 환경에서도 흐름(Failure Chain 포함)을 추적할 수 있게 합니다. 특히 `RUN_METADATA` 이벤트를 통해 Git 커밋과 실험 버전을 명시하여 재현성을 보장합니다.
* `llm_client.py`: 실제 LLM API를 호출하거나 `mock_llm`을 호출하는 클라이언트 역할을 합니다.
* `failure_injection.py`: 실험 중 의도적으로 Crash나 Straggler를 발생시켜 시스템의 Fault Tolerance를 테스트합니다. (Queue Stall, Retry 시도 등은 파서를 통해 개별 집계됨)

### `architectures/` (아키텍처 구현체)
총 4개의 분산 아키텍처 모델이 구현되어 있습니다. 각 아키텍처는 동일한 워크로드를 각자의 방식으로 처리합니다.
1. **monolithic**: 단일 프로세스/에이전트가 모든 작업을 순차적으로 처리합니다. (비교를 위한 Baseline)
2. **master_worker**: 중앙의 Master가 작업을 여러 Worker에게 분배하고 취합합니다.
3. **queue_based**: 작업 생산자와 소비자를 Message Queue(예: Redis, RabbitMQ)로 분리한 비동기 아키텍처입니다.
4. **swarm**: 중앙 제어 없이 에이전트 간 직접 통신(P2P) 및 Handoff를 통해 작업을 처리하는 구조입니다.

### `workloads/` (실험 워크로드)
성능을 측정하기 위해 두 가지 극단적인 성격의 태스크가 준비되어 있습니다.
* **Task A (Map-Reduce Style)**: 병렬화가 쉬운 작업(예: 긴 문서를 여러 개로 쪼개어 각각 요약 후 병합). 병렬 처리 효율과 Aggregation 병목을 측정합니다.
* **Task B (Multi-Hop QA)**: 순차적 의존성이 강한 작업(예: 이전 에이전트의 결과가 다음 에이전트의 입력으로 들어감). 에이전트 간 Handoff 및 Coordination 오버헤드를 측정합니다.

### `runner/` (실행기)
실제 실험을 구동하는 진입점입니다.
* `run_experiment.py`: 단일 실험을 실행할 때 사용합니다.
* `batch_run.py`, `stress_test_run.py` 등: 여러 설정(Worker 수 변경, Failure 모드 변경 등)을 순차적으로 자동 실행하여 대량의 비교 데이터를 생성할 때 사용합니다.

---

## 4. 처음 시작하기 (Getting Started)

코드를 파악하기 위해 다음 순서로 살펴보시는 것을 권장합니다.

1. **설정 확인**: `configs/` 폴더 내의 YAML/JSON 파일들을 열어 어떤 변수(아키텍처, 워크로드, 워커 수 등)를 제어하는지 확인하세요.
2. **단일 실행 로직 추적**: `runner/run_experiment.py`를 열어봅니다. 이 파일이 설정을 로드하고 `RUN_METADATA`를 기록한 뒤, `architectures/` 내의 특정 아키텍처 실행기를 호출하는 과정을 따라가 보세요.
3. **아키텍처 비교**: `architectures/monolithic`의 코드와 `architectures/master_worker`의 코드를 비교해보며, 동일한 Task를 분산 처리할 때 코드가 어떻게 달라지는지 파악해보세요.
4. **로그 구조 이해**: 실험이 끝나면 `logs/` (또는 지정된 결과 디렉터리)에 `.jsonl` 파일이 생성됩니다. `core/logger.py`가 어떤 정보를 남기는지 확인하시고, `parser/metrics_parser.py`가 이 로그를 어떻게 읽어들여 p50/p99 Latency, Execution Time, Queue Depth(Max/P95), Dispatch Time 등의 세밀한 지표로 변환하는지 확인하시면 전체 흐름이 잡힙니다.

## 5. 유의 사항 및 다음 단계
* **Mock LLM vs Real LLM**: 단순 아키텍처 성능 테스트 시에는 비용과 시간 절약을 위해 `mock_llm` 환경을 사용해왔습니다. 실제 성능을 검증할 때는 설정을 변경하여 진짜 API를 타도록 조정해야 합니다.
* 프로젝트의 기획과 목표, 정의된 지표에 대한 더 자세한 문맥은 루트 디렉터리의 `plan.md` 및 `agent.md`를 참고해 주세요.
