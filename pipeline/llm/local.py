"""
pipeline.llm.local — Provider local usando Ollama.
No requiere internet. Modelos recomendados: mistral:7b (3060), llama3:70b (5070).
"""
import os
import ollama
from pipeline.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    """Analiza transcripts usando un modelo local a través de Ollama."""

    def __init__(self, model: str = None):
        self.model = model or os.getenv("OLLAMA_MODEL", "mistral:7b")

    def _call(self, prompt: str, temperature: float = 0.2) -> str:
        resp = ollama.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            format="json",            # fuerza salida JSON a nivel de sampler
            options={"temperature": temperature},
        )
        return resp["message"]["content"]

    def __repr__(self):
        return f"OllamaProvider(model={self.model})"
