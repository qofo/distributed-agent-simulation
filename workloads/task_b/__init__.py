import os
import json
import random
from typing import Dict, Any
from core.llm_client import generate_content

class TaskBAdapter:
    """
    Multi-Hop QA / Chained Agent Reasoning Workload Adapter.
    This adapter defines the contract for sequential, dependent steps.
    """
    def __init__(self, total_steps: int = 3):
        self.total_steps = total_steps

    def create_initial_state(self, query: str) -> Dict[str, Any]:
        """Creates the starting state for the multi-hop reasoning."""
        dataset_path = os.path.join("data", "hotpotqa_sample.json")
        try:
            with open(dataset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data:
                    selected = random.choice(data)
                    actual_query = selected["question"]
                else:
                    actual_query = query
        except (FileNotFoundError, json.JSONDecodeError):
            actual_query = query
            
        return {
            "current_step": 0,
            "total_steps": self.total_steps,
            "query": actual_query,
            "context": [],
            "is_complete": False
        }

    def process_step(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Processes one reasoning step using actual Gemini API."""
        if state.get("is_complete"):
            return state

        current_step = state["current_step"]
        query = state["query"]
        context_str = "\n".join(f"- {c}" for c in state["context"])
        
        # Generalized prompt for any Multi-Hop QA query
        prompt = f"""
Main Query: {query}

Context from previous steps:
{context_str if context_str else "No context yet."}

You are an advanced reasoning agent. We are currently at Step {current_step + 1} of {self.total_steps}.
Based on the Main Query and the Context from previous steps, determine the NEXT logical intermediate question to ask or the next piece of information to find, and then immediately answer it. If you have enough information to answer the Main Query directly, output the final answer.
Provide a concise and factual statement representing the insight gained in this step.
"""

        response = generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt.strip(),
            config={
                "system_instruction": "You are a precise analytical AI performing step-by-step reasoning. Output only the factual insight discovered in this step."
            }
        )
        new_insight = response.text.strip()
        
        updated_context = state["context"] + [new_insight]
        next_step = current_step + 1
        is_complete = (next_step >= self.total_steps)

        return {
            "current_step": next_step,
            "total_steps": self.total_steps,
            "query": state["query"],
            "context": updated_context,
            "is_complete": is_complete
        }
