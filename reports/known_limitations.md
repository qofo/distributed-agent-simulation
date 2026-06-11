# Known Limitations

이 문서는 실험 설계의 의도적 단순화와 측정값을 해석할 때 반드시 고려해야 할 제약 조건을 기술한다.

---

## 1. 인메모리 시뮬레이션 (단일 프로세스)

**실험 구성**: 모든 아키텍처(Monolithic, Master-Worker, Queue-Based, Swarm)는 단일 Python 프로세스 내에서 `threading.Thread`와 `queue.Queue`로 구현되어 있다.

**포함되지 않은 요소**:
- 네트워크 I/O, TCP 소켓 오버헤드, 직렬화 비용
- 프로세스 간 통신(IPC), 노드 분산
- 메시지 브로커(Redis, RabbitMQ 등)의 Persistence, ACK, Backpressure

**의도**: 네트워크 레이턴시 등 환경 변수를 제거하여 **아키텍처 패턴 자체의 조정(Coordination) 비용**만 순수하게 측정하기 위한 의도적 단순화이다.

**해석 주의**: 이 실험의 결과는 "아키텍처 패턴 간 조정 비용의 상대적 차이"를 보여주며, 실제 분산 배포 환경(예: Redis, Kubernetes)의 절대 수치와 직접 비교할 수 없다.

---

## 2. Swarm의 정적 라우팅

**실험 구성**: Swarm은 사전 정의된 라운드로빈 라우팅 테이블(`routing_table[step % worker_count]`)에 기반한다.

**포함되지 않은 요소**:
- 동적 합의 프로토콜 (Paxos, Raft 등)
- 에이전트 협상 및 역할 협의
- 부하 기반 동적 분배
- 에이전트 전문성(Capability) 기반 선택

**의도**: "중앙 조정자 없이 P2P Handoff가 발생할 때 발생하는 조정 비용의 측정"을 위한 의도적 단순화이다.

**향후 실험**: `swarm_v2`는 Idle 에이전트를 우선 선택하는 Load-Aware Routing을 적용한 비교 실험군이다. 두 결과를 비교하면 라우팅 전략 차이의 영향을 정량화할 수 있다. (사전 분석: 동시 active agent 수 분포가 2개 이상 ≥ 30%일 때 진행)

---

## 3. 로깅 오버헤드

**문제**: 현재 모든 로깅 호출(`worker_state`, `inference_start` 등)은 메인 실행 경로에서 동기적으로 발생한다. 아키텍처마다 이벤트 수가 다르기 때문에 로깅 오버헤드가 아키텍처별로 다를 수 있다.

**실험**: `--logger-mode` 플래그를 통한 3단계 비교 실험으로 측정.

| 실험군 | 설명 |
|---|---|
| `normal` | 정상 로깅 (기준값) |
| `disabled` | I/O 차단 (함수 호출 오버헤드 측정) |
| `null` | NullLogger (전체 로깅 비용 측정) |

**판단 기준**: 아키텍처 간 오버헤드 차이가 아키텍처 간 레이턴시 차이의 20%를 초과하면 비동기 로거 도입을 검토한다.

**측정 결과** ← P1-A 실험 완료 후 아래를 채워 넣음:

| 아키텍처 | 전체 로깅 오버헤드 (A-C) | I/O 오버헤드 (A-B) | 호출 오버헤드 (B-C) |
|---|---|---|---|
| Monolithic | — ms (—%) | — ms | — ms |
| Master-Worker | — ms (—%) | — ms | — ms |
| Queue-Based | — ms (—%) | — ms | — ms |
| Swarm | — ms (—%) | — ms | — ms |
| **아키텍처 간 오버헤드 차이** | — ms | — | — |
| **레이턴시 차이 대비 비율** | —% | — | — |
| **판정** | — | — | — |

---

## 4. Task B는 Chain-of-Thought 시뮬레이션

**실험 구성**: Multi-Hop QA는 Retrieval, Search, Tool Use 없이 LLM의 맥락 내 추론만으로 구성되며, 스텝 수는 설정값(`total_steps`)으로 고정된다.

**포함되지 않은 요소**:
- 외부 지식 검색 (Retrieval-Augmented Generation)
- Tool Calling, Web Search
- LLM이 스스로 종료 조건을 판단하는 동적 스텝 수

**의도**: "순차 의존성이 강한 작업에서 아키텍처별 조정 비용(Coordination Overhead)"을 측정하기 위한 의도된 제약이다. 스텝 수를 고정함으로써 실험 간 비교 가능성을 유지한다.

---

## 5. 반복 실험의 분산 (재현성)

**문제**: LLM API 응답 지연의 변동과 OS 스레드 스케줄링 노이즈로 인해 단일 실행 결과가 흔들릴 수 있다.

**실험**: `analyzer/reproducibility_check.py`로 동일 config N회 반복 실행하여 변동계수(CV)와 Bootstrap 95% CI를 계산.

**측정 결과** ← P1.5 실험 완료 후 아래를 채워 넣음:

| 아키텍처 | N | mean (s) | std (s) | CV (%) | 95% CI | 판정 |
|---|---|---|---|---|---|---|
| Monolithic | — | — | — | — | — | — |
| Master-Worker | — | — | — | — | — | — |
| Queue-Based | — | — | — | — | — | — |
| Swarm | — | — | — | — | — | — |

**판단 기준**:
- CV < 10%: 안정. 5회 반복으로 충분.
- CV 10~20%: 주의. 10회 이상 반복 권장.
- CV > 20%: 위험. 실험 조건 재검토 필요.
