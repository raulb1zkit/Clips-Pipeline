"""
pipeline.llm.base — Clase abstracta que deben implementar todos los providers LLM.
"""
from abc import ABC, abstractmethod
import json
import os
import re


PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "prompts")


def load_prompt(content_type: str, transcript: dict) -> str:
    """Carga el prompt del archivo .txt e inyecta transcript y duration."""
    prompt_path = os.path.join(PROMPTS_DIR, f"{content_type}.txt")
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt no encontrado: {prompt_path}")
    template = open(prompt_path, encoding="utf-8").read()
    full_text = " ".join(s["text"] for s in transcript["segments"])
    return (template
            .replace("{transcript_text}", full_text)
            .replace("{duration}", str(round(transcript["duration"], 2))))


def clean_json(raw: str) -> dict:
    """
    Limpia la respuesta del LLM y parsea el JSON.
    Maneja markdown code fences (```json ... ```) y texto extra alrededor.
    """
    # Eliminar fences de markdown
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    # Extraer el primer bloque JSON encontrado
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"No se encontró JSON válido en la respuesta: {raw[:200]}")
    return json.loads(match.group())


class LLMProvider(ABC):
    """
    Interfaz común para todos los providers de análisis semántico.
    Subclases deben implementar _call(prompt) que devuelve el texto raw del LLM.
    """

    MAX_RETRIES = 2

    def generate(self, transcript: dict, content_type: str = "gaming") -> dict:
        """
        Genera candidatos a clips a partir del transcript.
        Incluye retry automático con temperatura reducida si el JSON falla.
        """
        prompt = load_prompt(content_type, transcript)
        last_error = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                raw = self._call(prompt, temperature=0.2 if attempt == 0 else 0.1)
                return clean_json(raw)
            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                print(f"[LLM] Intento {attempt + 1} fallido: {e}. Reintentando...")

        raise RuntimeError(
            f"El LLM no devolvió JSON válido tras {self.MAX_RETRIES + 1} intentos. "
            f"Último error: {last_error}"
        )

    @abstractmethod
    def _call(self, prompt: str, temperature: float = 0.2) -> str:
        """Llama al backend y devuelve el texto raw de la respuesta."""
        ...
