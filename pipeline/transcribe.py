"""
pipeline.transcribe — Fase 2: Transcripción ASR con faster-whisper.
"""
import os
import ctypes

# faster-whisper needs libcublas.so.12 but it is not in a standard system path
# on this machine. Ollama bundles it under cuda_v12 — add that to LD_LIBRARY_PATH
# so the dynamic linker can find it before the module is imported.
_OLLAMA_CUDA12 = "/usr/local/lib/ollama/cuda_v12"
_ldpath = os.environ.get("LD_LIBRARY_PATH", "")
if _OLLAMA_CUDA12 not in _ldpath.split(":"):
    os.environ["LD_LIBRARY_PATH"] = f"{_OLLAMA_CUDA12}:{_ldpath}" if _ldpath else _OLLAMA_CUDA12
    # Force the dynamic linker to pick up the new path for subsequent dlopen calls
    try:
        ctypes.CDLL(f"{_OLLAMA_CUDA12}/libcublas.so.12")
    except OSError:
        pass  # Will fail gracefully; the env var set above still helps child processes

from faster_whisper import WhisperModel


_model_cache: dict = {}


def _get_model(model_size: str, device: str, compute_type: str) -> WhisperModel:
    """Carga el modelo en caché para no recargarlo entre llamadas."""
    key = (model_size, device, compute_type)
    if key not in _model_cache:
        print(f"[Whisper] Cargando modelo {model_size} ({compute_type}) en {device}...")
        _model_cache[key] = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _model_cache[key]


def transcribe(audio_path: str,
               model_size: str = None,
               device: str = None,
               compute_type: str = None,
               language: str = "es") -> dict:
    """
    Transcribe el audio y devuelve el schema estándar del pipeline.

    Args:
        audio_path:   ruta al WAV de entrada (salida de audio.py)
        model_size:   'medium' (dev) | 'large-v2' (prod). Usa WHISPER_MODEL del .env si None.
        device:       'cuda' | 'cpu'. Usa WHISPER_DEVICE del .env si None.
        compute_type: 'int8' (dev) | 'float16' (prod). Usa WHISPER_COMPUTE_TYPE del .env si None.
        language:     idioma forzado. 'es' por defecto.

    Returns:
        {
            "segments": [{"id", "start", "end", "text"}, ...],
            "duration": float
        }
    """
    model_size   = model_size   or os.getenv("WHISPER_MODEL", "medium")
    device       = device       or os.getenv("WHISPER_DEVICE", "cuda")
    compute_type = compute_type or os.getenv("WHISPER_COMPUTE_TYPE", "int8")

    model = _get_model(model_size, device, compute_type)
    segments_raw, info = model.transcribe(
        audio_path,
        beam_size=3,
        language=language,
        vad_filter=True,      # filtra silencios → segmentos más limpios
    )
    segments = [
        {
            "id": i,
            "start": round(s.start, 3),
            "end":   round(s.end, 3),
            "text":  s.text.strip(),
        }
        for i, s in enumerate(segments_raw)
    ]
    return {"segments": segments, "duration": info.duration}
