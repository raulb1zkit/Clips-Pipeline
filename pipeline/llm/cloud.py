"""
pipeline.llm.cloud — Provider cloud usando MiniMax-M2.5.
Usa el protocolo compatible con OpenAI (solo cambia base_url y api_key).
"""
import os
from openai import OpenAI
from pipeline.llm.base import LLMProvider


class MiniMaxProvider(LLMProvider):
    """Analiza transcripts usando MiniMax-M2.5 vía API cloud."""

    BASE_URL = "https://api.minimax.io/v1"

    def __init__(self, model: str = None, api_key: str = None):
        self.model = model or os.getenv("MINIMAX_MODEL", "MiniMax-M2.5")
        api_key = api_key or os.getenv("MINIMAX_API_KEY")
        if not api_key:
            raise ValueError(
                "MINIMAX_API_KEY no está configurado. "
                "Añádelo al .env o pásalo como argumento."
            )
        self.client = OpenAI(base_url=self.BASE_URL, api_key=api_key)

    def _call(self, prompt: str, temperature: float = 0.2) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return resp.choices[0].message.content

    def __repr__(self):
        return f"MiniMaxProvider(model={self.model})"
