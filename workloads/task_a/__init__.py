import os
import json
import random
from typing import List, Dict, Any
from core.llm_client import generate_content

class TaskAAdapter:
    """
    Map-Reduce Style Summarization Workload Adapter.
    This adapter defines the contract for splitting an input document,
    processing individual chunks, and aggregating the results.
    """
    def __init__(self, chunk_count: int = 1):
        self.chunk_count = chunk_count

    def split(self, input_data: str) -> List[Dict[str, Any]]:
        """Splits a random CNN-Dailymail article into independent chunks."""
        dataset_path = os.path.join("data", "cnn_dailymail_sample.json")
        try:
            with open(dataset_path, "r", encoding="utf-8") as f:
                articles = json.load(f)
                if articles:
                    selected_article = random.choice(articles)
                    content = selected_article["article"]
                else:
                    content = input_data
        except (FileNotFoundError, json.JSONDecodeError):
            content = input_data
            
        # Split into paragraphs
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        # We will split paragraphs into self.chunk_count chunks
        import math
        chunk_size = math.ceil(len(paragraphs) / self.chunk_count) if self.chunk_count > 0 else 1
        
        chunks = []
        for i in range(self.chunk_count):
            start = i * chunk_size
            end = min((i + 1) * chunk_size, len(paragraphs))
            chunk_content = "\n".join(paragraphs[start:end]) if start < len(paragraphs) else "No content"
            
            chunks.append({
                "chunk_id": i,  # integer is safer
                "content": chunk_content
            })
        return chunks

    def process_chunk(self, chunk: Dict[str, Any], context: Dict[str, Any] = None) -> str:
        """Processes a single chunk using actual Gemini API."""
        content = chunk["content"]
        if content == "No content":
            return ""
            
        prompt = f"Summarize the following text in one sentence:\n\n{content}"
        
        response = generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config={
                "system_instruction": "You are a highly efficient summarization AI. Output only the summarized text without any conversational filler."
            },
            context=context
        )
        return response.text.strip()

    def aggregate(self, results: List[str]) -> str:
        """Aggregates all chunk summaries into a final output using Gemini."""
        valid_results = [r for r in results if r]
        combined_summaries = "\n".join(f"- {r}" for r in valid_results)
        
        prompt = f"Here are several sentence summaries of different parts of a document. Synthesize them into one coherent overall summary paragraph:\n\n{combined_summaries}"
        
        response = generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt,
            config={
                "system_instruction": "You are a master editor. Combine the given bullet points into a single flowing paragraph."
            }
        )
        return response.text.strip()
