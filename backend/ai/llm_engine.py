from __future__ import annotations


class LLMInsightEngine:
    """LLM-ready placeholder.

    Keep the interface stable. Later, connect this to OpenAI, Azure OpenAI,
    local Ollama, or another provider.
    """

    def generate(self, dataset_profile: dict, question: str | None = None) -> str:
        return (
            "LLM engine is not configured yet. The MVP is currently using "
            "the rule-based insight engine."
        )
