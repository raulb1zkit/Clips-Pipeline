"""
pipeline.validate — Fase 4: Validación y corrección de clips propuestos por el LLM.

MÓDULO CRÍTICO 🔥 — El sistema NUNCA confía en el output del LLM directamente.
Todo clip propuesto pasa por este módulo antes de tocar un solo frame de vídeo.
"""


# ──────────────────────────────────────────────────────────────
# Utilidades
# ──────────────────────────────────────────────────────────────

def snap_to_segment_start(t: float, segments: list, window: float = 5.0) -> float:
    """Ajusta t al inicio del segmento ASR más cercano dentro de 'window' segundos."""
    nearby = [s for s in segments if abs(s["start"] - t) < window]
    if not nearby:
        return t
    return min(nearby, key=lambda s: abs(s["start"] - t))["start"]


def snap_to_segment_end(t: float, segments: list, window: float = 5.0) -> float:
    """Ajusta t al final del segmento ASR más cercano dentro de 'window' segundos."""
    nearby = [s for s in segments if abs(s["end"] - t) < window]
    if not nearby:
        return t
    return min(nearby, key=lambda s: abs(s["end"] - t))["end"]


def overlaps(a: dict, b: dict) -> bool:
    """Devuelve True si los clips a y b se solapan."""
    return not (a["end"] <= b["start"] or a["start"] >= b["end"])


# ──────────────────────────────────────────────────────────────
# Pipeline de validación
# ──────────────────────────────────────────────────────────────

def validate(candidates: dict, transcript: dict,
             min_dur: float = 15.0, max_dur: float = 90.0,
             margin: float = 2.0, max_clips: int = 5) -> dict:
    """
    Valida y corrige los clips propuestos por el LLM.

    Pasos:
      1. Bounds check     — timestamps dentro de [0, duration]
      2. Duration filter  — duración dentro de [min_dur, max_dur]
      3. Snap to ASR      — alinea a bordes reales de segmentos de transcripción
      4. Margin expansion — añade 'margin' segundos de contexto natural
      5. Overlap removal  — elimina solapamientos, conserva mayor score
      6. Top-N cap        — devuelve como máximo 'max_clips' clips

    Args:
        candidates: salida cruda del LLM — {clips: [...]}
        transcript: salida de transcribe() — {segments, duration}
        min_dur:    duración mínima válida (s)
        max_dur:    duración máxima válida (s)
        margin:     segundos de margen a añadir en cada extremo
        max_clips:  número máximo de clips a devolver (los de mayor score)

    Returns:
        {clips: [...]} — clips validados, ordenados por tiempo, sin solapamientos
    """
    duration = float(transcript["duration"])
    segments = transcript["segments"]
    clips = candidates.get("clips", [])
    valid = []

    for clip in clips:
        s = max(0.0, float(clip.get("start", 0)))
        e = min(duration, float(clip.get("end", 0)))

        # 1. Bounds check
        if s >= e:
            continue

        # 2. Duration filter
        if (e - s) < min_dur or (e - s) > max_dur:
            continue

        # 3. Snap to transcript
        s = snap_to_segment_start(s, segments)
        e = snap_to_segment_end(e, segments)

        # 4. Margin expansion
        s = max(0.0, s - margin)
        e = min(duration, e + margin)

        clip["start"]     = round(s, 3)
        clip["end"]       = round(e, 3)
        clip["validated"] = True
        valid.append(clip)

    # 5. Overlap removal (conserva el de mayor score)
    valid.sort(key=lambda x: -x.get("score", 0))
    no_overlap = []
    for clip in valid:
        if not any(overlaps(clip, kept) for kept in no_overlap):
            no_overlap.append(clip)

    # 6. Top-N cap — quedarse solo con los mejores clips
    no_overlap = no_overlap[:max_clips]

    # Ordenar cronológicamente para el procesado posterior
    no_overlap.sort(key=lambda x: x["start"])
    return {"clips": no_overlap}
