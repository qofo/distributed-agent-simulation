# Mock LLM Service (가상 LLM 서비스)

이 서비스는 분산 에이전트 시뮬레이션 환경(Harness)에서 사용되는 확정적(Deterministic) Mock LLM 서비스입니다. 실제 상용 LLM의 호출 비용과 응답 시간 편차를 피하고, 재현 가능한 실험을 위해 구성 가능한 지연 시간(latency)과 일관된 출력(stable outputs)을 제공합니다.

## 필수 구성 요소 (Requirements)
```bash
pip install -r requirements.txt
```

## 서버 실행 방법 (Running the Server)
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## API 엔드포인트
**POST /generate**

### 요청 본문 (Request Body - JSON)
- `prompt` (문자열, 필수): LLM에 전달할 프롬프트 내용입니다.
- `latency_ms` (정수, 선택, 기본값=0): 인위적으로 주입할 지연 시간(밀리초)입니다.
- `deterministic` (부울, 선택, 기본값=true): `true`일 경우, 프롬프트 내용의 해시(hash)를 기반으로 항상 동일한 응답을 반환합니다.
- `seed` (정수, 선택): 확정적 응답을 다양하게 만들기 위해 추가할 수 있는 선택적 시드(seed) 값입니다.

### 응답 본문 (Response - JSON)
- `response` (문자열): 가상으로 생성된 텍스트 응답입니다.
- `metadata` (객체): `latency_injected_ms` (주입된 지연 시간) 및 `process_time_ms` (실제 처리 소요 시간)를 포함한 실행 메타데이터입니다.
