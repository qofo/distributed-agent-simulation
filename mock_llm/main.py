import asyncio
import hashlib
import time
import logging
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional

# 로깅 설정 (요청 처리 상태를 터미널과 로그에 출력하기 위함)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("mock_llm")

# FastAPI 애플리케이션 초기화
app = FastAPI(title="Deterministic Mock LLM", description="분산 에이전트 시뮬레이션을 위한 가상 LLM API")

# 요청(Request) 데이터 스키마 정의
class GenerateRequest(BaseModel):
    prompt: str
    latency_ms: int = Field(default=0, description="인위적으로 주입할 지연 시간(밀리초)")
    deterministic: bool = Field(default=True, description="True일 경우, 프롬프트 해시에 기반한 고정된 응답 반환")
    seed: Optional[int] = Field(default=None, description="확정적 난수 생성을 위한 선택적 시드(Seed) 값")

# 응답(Response) 데이터 스키마 정의
class GenerateResponse(BaseModel):
    response: str
    metadata: dict

@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    # 처리 시작 시간 기록
    start_time = time.time()
    logger.info(f"요청 수신됨: latency_ms={request.latency_ms}, deterministic={request.deterministic}")
    
    # 인위적 지연(Latency) 주입: 실험 환경에서 네트워크/추론 지연을 모사하기 위함
    if request.latency_ms > 0:
        await asyncio.sleep(request.latency_ms / 1000.0)
        
    # 가상 응답 텍스트 생성 로직
    if request.deterministic:
        # 확정적(Deterministic) 모드: 프롬프트와 시드를 조합하여 항상 동일한 해시값을 생성
        hash_input = request.prompt
        if request.seed is not None:
            hash_input += str(request.seed)
        
        # MD5 해시를 사용하여 일관성 있는 짧은 문자열 생성
        prompt_hash = hashlib.md5(hash_input.encode('utf-8')).hexdigest()
        response_text = f"프롬프트에 대한 가상 응답입니다. Hash: {prompt_hash[:8]}"
    else:
        # 비확정적(Random) 모드: 현재 시간을 기반으로 매번 다른 응답 생성
        random_suffix = str(time.time())[-6:]
        response_text = f"가상 랜덤 응답입니다. Random: {random_suffix}"
        
    # 총 처리 소요 시간 계산 (밀리초 단위)
    process_time_ms = int((time.time() - start_time) * 1000)
    
    # 평가(Evaluation) 및 분석을 위해 반환할 메타데이터 구성
    metadata = {
        "latency_injected_ms": request.latency_ms,
        "process_time_ms": process_time_ms,
        "deterministic": request.deterministic,
        "seed": request.seed
    }
    
    logger.info(f"요청 처리 완료. 소요 시간: {process_time_ms}ms")
    return GenerateResponse(response=response_text, metadata=metadata)
