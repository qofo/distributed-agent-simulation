from typing import Dict, Any

class TaskBAdapter:
    """
    Multi-Hop QA / Chained Agent Reasoning Workload Adapter.
    This adapter defines the contract for sequential, dependent steps.
    """
    def __init__(self, total_steps: int = 3):
        self.total_steps = total_steps

    def create_initial_state(self, query: str) -> Dict[str, Any]:
        """Creates the starting state for the multi-hop reasoning."""
        return {
            "current_step": 0,
            "total_steps": self.total_steps,
            "query": query,
            "context": [],
            "is_complete": False
        }

    def process_step(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Processes one reasoning step and returns the updated state."""
        if state.get("is_complete"):
            return state

        current_step = state["current_step"]
        # Mock LLM derivation
        new_insight = f"Insight from step {current_step}"
        
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
