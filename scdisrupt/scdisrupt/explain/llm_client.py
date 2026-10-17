"""LLM client and prompt templates for explanation and executive briefing."""
import os
from typing import Any, Dict, List, Optional

from scdisrupt.disruptions.cascade import CascadeAnalysis
from scdisrupt.scoring.counterfactual import PlanSimulationResult
from scdisrupt.scoring.scorer import ScoredPlan


class LLMExplainerClient:
    """Wrapper that calls Anthropic Claude API if available and key configured, 

    with high-quality deterministic structured fallback templates when offline.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        self._client = None

        if self.api_key:
            try:
                import anthropic  # type: ignore
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except Exception:
                self._client = None

    @property
    def is_live(self) -> bool:
        return self._client is not None

    def call_llm(self, system_prompt: str, user_prompt: str, fallback_text: str) -> str:
        """Call Claude LLM or fallback seamlessly."""
        if not self._client:
            return fallback_text

        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=1500,
                temperature=0.2,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text
        except Exception:
            return fallback_text
