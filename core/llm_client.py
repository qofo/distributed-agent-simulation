import os
import threading
import logging
import time
from typing import List, Any
from dotenv import load_dotenv

# Initialize google-genai
from google import genai
from google.genai import errors
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, retry_if_exception

load_dotenv()

class APIKeyManager:
    def __init__(self):
        self.lock = threading.Lock()
        
        # Load keys from .env
        self.keys = []
        for i in range(1, 10):
            key = os.environ.get(f"GEMINI_API_KEY{i}")
            if key:
                self.keys.append(key)
                
        if not self.keys:
            # Fallback to single GEMINI_API_KEY
            key = os.environ.get("GEMINI_API_KEY")
            if key:
                self.keys.append(key)
                
        if not self.keys:
            logging.warning("No GEMINI_API_KEYs found in environment.")
            
        self.clients = [genai.Client(api_key=k) for k in self.keys]
        self.current_idx = 0
        
    def get_client(self):
        with self.lock:
            if not self.clients:
                raise ValueError("No Gemini API clients available. Check your .env file.")
            return self.clients[self.current_idx]
            
    def rotate_key(self):
        with self.lock:
            old_idx = self.current_idx
            self.current_idx = (self.current_idx + 1) % len(self.clients)
            logging.warning(f"Rotated API Key from Index {old_idx} to {self.current_idx}")

# Global Manager
key_manager = APIKeyManager()

def is_rate_limit_error(exception: Exception) -> bool:
    """Check if the exception is a 429 or 503 error."""
    if isinstance(exception, errors.APIError):
        if exception.code in (429, 503):
            return True
    return False

# Retry on rate limit errors with exponential backoff (up to 5 attempts)
def log_retry(retry_state):
    context = retry_state.kwargs.get("context")
    if context:
        logger = context.get("logger")
        if logger:
            logger.api_429_error(
                trace_id=context.get("trace_id", "unknown"),
                architecture=context.get("architecture", "unknown"),
                worker_id=context.get("worker_id", "unknown")
            )

@retry(
    retry=retry_if_exception(is_rate_limit_error),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
    before_sleep=log_retry
)
def _generate_content_with_backoff(model: str, contents: Any, config: Any = None, context: Any = None):
    client = key_manager.get_client()
    try:
        if config:
            response = client.models.generate_content(model=model, contents=contents, config=config)
        else:
            response = client.models.generate_content(model=model, contents=contents)
            
        if context and "logger" in context:
            logger = context["logger"]
            ans = response.text.strip() if response and hasattr(response, "text") and response.text else ""
            logger.llm_response(
                trace_id=context.get("trace_id", "unknown"),
                architecture=context.get("architecture", "unknown"),
                task_id=context.get("task_id", "llm-call"),
                worker_id=context.get("worker_id", "unknown"),
                prompt=str(contents),
                response=ans
            )
        return response
    except errors.APIError as e:
        if e.code == 429:
            # 429 Resource Exhausted / Quota Exceeded. Rotate key and raise so Tenacity retries.
            logging.warning("Received 429 Rate Limit. Rotating key.")
            key_manager.rotate_key()
        raise e

def generate_content(model: str, contents: Any, config: Any = None, context: Any = None):
    """Wrapper to generate content with key rotation and retry logic."""
    return _generate_content_with_backoff(model=model, contents=contents, config=config, context=context)
