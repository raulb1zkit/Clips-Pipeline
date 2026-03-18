"""
pipeline.cutter — Fase 5: Corte de clips con FFmpeg en modo híbrido.
Modo híbrido: -ss antes del -i (rápido) + re-encode (preciso a nivel de frame).
"""
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor


def cut_one(video_path: str, clip: dict, index: int,
            output_dir: str = "cache/clips") -> str:
    """
    Corta un único clip del vídeo de entrada.

    Args:
        video_path: vídeo original
        clip:       {start, end, ...} (salida validada de validate.py)
        index:      número de clip para el nombre de archivo
        output_dir: carpeta de salida

    Returns:
        Ruta al clip cortado (cache/clips/clip_NNN_raw.mp4)
    """
    os.makedirs(output_dir, exist_ok=True)
    out = os.path.join(output_dir, f"clip_{index:03d}_raw.mp4")
    s, e = clip["start"], clip["end"]
    dur = e - s

    # Modo híbrido: -ss antes del -i busca keyframe más cercano.
    # El segundo -ss 1 corrige el offset → corte preciso a nivel de frame.
    cmd = [
        "ffmpeg",
        "-ss", str(max(0, s - 1)),
        "-i", video_path,
        "-ss", "1",
        "-to", str(dur),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-y", out
    ]
    subprocess.run(cmd, check=True)
    return out


def cut_all(video_path: str, clips: list, workers: int = None) -> list:
    """
    Corta todos los clips en paralelo usando ThreadPoolExecutor.

    Args:
        video_path: vídeo original
        clips:      lista de clips validados
        workers:    número de FFmpeg paralelos (None = usa MAX_WORKERS del .env)

    Returns:
        Lista ordenada de rutas a clips cortados
    """
    workers = workers or int(os.getenv("MAX_WORKERS", 2))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = [ex.submit(cut_one, video_path, clip, i)
                   for i, clip in enumerate(clips)]
        return [f.result() for f in futures]
