"""
pipeline.audio — Fase 1: Extracción de audio del vídeo de entrada.
"""
import subprocess
import shutil
import os


def extract_audio(video_path: str, output_path: str = "cache/audio.wav") -> str:
    """
    Extrae el audio del vídeo en formato WAV mono 16kHz, optimizado para Whisper.

    Args:
        video_path:  ruta al fichero de vídeo de entrada (.mp4, .mkv, etc.)
        output_path: ruta de salida del WAV (por defecto cache/audio.wav)

    Returns:
        output_path — ruta al fichero de audio generado
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError(
            "ffmpeg not found. Install it with: sudo apt install ffmpeg"
        )
    cmd = [
        ffmpeg, "-i", video_path,
        "-ac", "1",          # mono — ASR más estable
        "-ar", "16000",      # 16 kHz — estándar Whisper
        "-vn",               # sin vídeo
        "-y",                # sobreescribir sin preguntar
        output_path
    ]
    subprocess.run(cmd, check=True)
    return output_path
