"""
pipeline.llm.base — Clase abstracta que deben implementar todos los providers LLM.
"""
from abc import ABC, abstractmethod
import json
import os
import re


PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "prompts")

# Ventana de tiempo por chunk (segundos). 15 min es seguro para modelos con ~8k ctx.
CHUNK_WINDOW_SECS = int(os.getenv("LLM_CHUNK_WINDOW", "900"))   # 15 min
# Solapamiento entre chunks para no perder momentos en los bordes
CHUNK_OVERLAP_SECS = int(os.getenv("LLM_CHUNK_OVERLAP", "60"))  # 1 min


def load_prompt(content_type: str, transcript_text: str, duration: float) -> str:
    """Carga el prompt del archivo .txt e inyecta transcript y duration."""
    prompt_path = os.path.join(PROMPTS_DIR, f"{content_type}.txt")
    if not os.path.exists(prompt_path):
        raise FileNotFoundError(f"Prompt no encontrado: {prompt_path}")
    template = open(prompt_path, encoding="utf-8").read()
    return (template
            .replace("{transcript_text}", transcript_text)
            .replace("{duration}", str(round(duration, 2))))


def _format_transcript_with_timestamps(segments: list) -> str:
    """
    Formatea cada segmento con su timestamp real en formato [HH:MM:SS],
    seguido del texto. Así el LLM tiene anclas temporales exactas y no
    tiene que inventar timestamps.

    Ejemplo de línea:
      [00:02:11 → 00:02:19] Esto que dijo el jugador fue increíble
    """
    lines = []
    for seg in segments:
        start = float(seg["start"])
        end   = float(seg["end"])
        h_s, m_s = divmod(int(start), 3600)
        m_s, s_s = divmod(m_s, 60)
        h_e, m_e = divmod(int(end), 3600)
        m_e, s_e = divmod(m_e, 60)
        ts = f"[{h_s:02d}:{m_s:02d}:{s_s:02d} → {h_e:02d}:{m_e:02d}:{s_e:02d}]"
        lines.append(f"{ts} {seg['text'].strip()}")
    return "\n".join(lines)



def chunk_transcript(transcript: dict,
                     window: float = CHUNK_WINDOW_SECS,
                     overlap: float = CHUNK_OVERLAP_SECS) -> list[dict]:
    """
    Divide el transcript en ventanas de tiempo solapadas.

    Args:
        transcript: {segments: [...], duration: float}
        window:     duración de cada chunk en segundos
        overlap:    solapamiento entre chunks en segundos

    Returns:
        Lista de dicts: {segments, duration, chunk_start, chunk_end}
    """
    total = float(transcript["duration"])
    segments = transcript["segments"]
    chunks = []

    t = 0.0
    while t < total:
        end = min(t + window, total)
        segs = [s for s in segments if s["start"] >= t and s["end"] <= end]
        if segs:
            chunks.append({
                "segments": segs,
                "duration": end,          # el LLM necesita el tope absoluto del vídeo
                "chunk_start": t,
                "chunk_end": end,
            })
        t += window - overlap
        if t >= total:
            break

    return chunks


def _extract_first_json_object(text: str) -> str:
    """
    Extrae el primer objeto JSON completo usando conteo de llaves.
    Evita el problema del regex greedy que captura texto extra tras el JSON.
    """
    start = text.find("{")
    if start == -1:
        raise ValueError(f"No se encontró '{{' en la respuesta: {text[:200]}")
    depth = 0
    in_string = False
    escape_next = False
    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError(f"JSON incompleto (llaves no balanceadas): {text[:200]}")


def clean_json(raw: str) -> dict:
    """
    Limpia la respuesta del LLM y parsea el JSON.
    Maneja markdown code fences (```json ... ```) y texto extra antes/después.
    """
    # Eliminar fences de markdown
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    # Extraer el primer objeto JSON completo (balanceo de llaves, no regex greedy)
    json_str = _extract_first_json_object(raw)
    return json.loads(json_str)


class LLMProvider(ABC):
    """
    Interfaz común para todos los providers de análisis semántico.
    Subclases deben implementar _call(prompt) que devuelve el texto raw del LLM.
    """

    MAX_RETRIES = 2

    def generate(self, transcript: dict, content_type: str = "gaming") -> dict:
        """
        Genera candidatos a clips a partir del transcript.
        Si el transcript es largo, lo divide en chunks y combina los resultados.
        """
        total_duration = float(transcript["duration"])

        # Para vídeos cortos (≤ ventana + solapamiento), proceso directo sin chunking
        if total_duration <= CHUNK_WINDOW_SECS + CHUNK_OVERLAP_SECS:
            return self._generate_single(transcript, content_type, total_duration)

        # Para vídeos largos: chunking
        chunks = chunk_transcript(transcript, CHUNK_WINDOW_SECS, CHUNK_OVERLAP_SECS)
        print(f"[LLM] Vídeo largo ({total_duration/60:.1f} min) → {len(chunks)} chunks de ~{CHUNK_WINDOW_SECS/60:.0f} min")

        all_clips = []
        for idx, chunk in enumerate(chunks):
            t0, t1 = chunk["chunk_start"], chunk["chunk_end"]
            print(f"[LLM] Chunk {idx+1}/{len(chunks)}: {t0/60:.1f}–{t1/60:.1f} min  ({len(chunk['segments'])} segs)")
            chunk_result = self._generate_single(chunk, content_type, total_duration)
            clips = chunk_result.get("clips", [])
            print(f"[LLM]   → {len(clips)} candidatos en este chunk")
            all_clips.extend(clips)

        return {"clips": all_clips}

    def _generate_single(self, chunk: dict, content_type: str,
                         total_duration: float) -> dict:
        """
        Procesa un único chunk/transcript y devuelve {clips: [...]}.
        Incluye retry automático con temperatura reducida si el JSON falla.
        """
        # Formatear con timestamps reales para que el LLM no los invente
        transcript_text = _format_transcript_with_timestamps(chunk["segments"])
        prompt = load_prompt(content_type, transcript_text, total_duration)
        last_error = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                raw = self._call(prompt, temperature=0.2 if attempt == 0 else 0.1)
                result = clean_json(raw)
                # Sanity check: el modelo a veces devuelve timestamps relativos al chunk
                # Si todos los clips están contenidos en la ventana del chunk,
                # los dejamos pasar (el validador los verificará con total_duration).
                return result
            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                print(f"[LLM] Intento {attempt + 1} fallido: {e}. Reintentando...")

        print(f"[LLM] ⚠️  Chunk descartado tras {self.MAX_RETRIES + 1} intentos: {last_error}")
        return {"clips": []}

    @abstractmethod
    def _call(self, prompt: str, temperature: float = 0.2) -> str:
        """Llama al backend y devuelve el texto raw de la respuesta."""
        ...
