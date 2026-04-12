"""
pipeline.llm — Módulo de análisis semántico con soporte local (Ollama) y cloud (MiniMax-M2.5).
"""
from pipeline.llm.base import LLMProvider
from pipeline.llm.local import OllamaProvider
from pipeline.llm.cloud import MiniMaxProvider

import os


def get_provider(provider: str = None) -> LLMProvider:
    """
    Devuelve el provider configurado.
    Prioridad: argumento explícito > LLM_PROVIDER en .env > 'local'
    """
    name = provider or os.getenv("LLM_PROVIDER", "local")
    if name == "local":
        return OllamaProvider()
    elif name == "minimax":
        return MiniMaxProvider()
    else:
        raise ValueError(f"Provider desconocido: '{name}'. Usa 'local' o 'minimax'.")


def generate_candidates(transcript: dict, content_type: str = "gaming",
                        provider: str = None) -> dict:
    """
    Interfaz única para el análisis semántico.
    El resto del pipeline no necesita saber qué backend se usa.

    Args:
        transcript:   salida de transcribe() — {segments, duration}
        content_type: 'gaming' | 'podcast'
        provider:     'local' | 'minimax' | None (usa LLM_PROVIDER del .env)

    Returns:
        {clips: [{start, end, title, score}]}  — sin validar (pasar por validate.py)
    """
    llm = get_provider(provider)
    return llm.generate(transcript, content_type)
