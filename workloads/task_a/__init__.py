from typing import List, Dict, Any

class TaskAAdapter:
    """
    Map-Reduce Style Summarization Workload Adapter.
    This adapter defines the contract for splitting an input document,
    processing individual chunks, and aggregating the results.
    """
    def __init__(self, chunk_count: int = 1):
        self.chunk_count = chunk_count

    def split(self, input_data: str) -> List[Dict[str, Any]]:
        """Splits the input data into independent chunks."""
        chunks = []
        for i in range(self.chunk_count):
            chunks.append({
                "chunk_id": f"chunk-{i}",
                "content": f"Mock content segment {i} of {input_data}"
            })
        return chunks

    def process_chunk(self, chunk: Dict[str, Any]) -> str:
        """Processes a single chunk (Mock LLM Inference)."""
        return f"Summary of {chunk['chunk_id']}"

    def aggregate(self, results: List[str]) -> str:
        """Aggregates all chunk summaries into a final output."""
        return " | ".join(results)
