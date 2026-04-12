"""
pipeline.brand — Fase 7: Branding final (subtítulos ASS + logo + lower third).
Un solo pass de FFmpeg con filtergraph completo.
"""
import os
import subprocess


# ──────────────────────────────────────────────────────────────
# Subtítulos ASS
# ──────────────────────────────────────────────────────────────

def _fmt_ass_time(t: float) -> str:
    """Convierte segundos a formato ASS: H:MM:SS.cc"""
    t = max(0.0, t)
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def create_ass(segments: list, clip_start: float, clip_end: float,
               output: str = "cache/subs_tmp.ass") -> str:
    """
    Genera un archivo de subtítulos ASS sincronizado con el clip.

    Args:
        segments:   lista de segmentos ASR del transcript completo
        clip_start: tiempo de inicio del clip en el vídeo original (s)
        clip_end:   tiempo de fin del clip en el vídeo original (s)
        output:     ruta del .ass generado

    Returns:
        Ruta al archivo ASS generado
    """
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "PlayResX: 1080\n"
        "PlayResY: 1920\n"
        "[V4+ Styles]\n"
        "Format: Name,Fontname,Fontsize,PrimaryColour,Bold,Shadow,Alignment\n"
        "Style: Default,Arial,72,&H00FFFFFF,1,2,2\n"
        "[Events]\n"
        "Format: Layer,Start,End,Style,Text"
    )
    os.makedirs(os.path.dirname(output), exist_ok=True)
    lines = [header]
    for seg in segments:
        if seg["end"] < clip_start or seg["start"] > clip_end:
            continue
        s = seg["start"] - clip_start
        e = seg["end"] - clip_start
        text = seg["text"].replace("\n", " ")
        lines.append(f"Dialogue: 0,{_fmt_ass_time(s)},{_fmt_ass_time(e)},Default,,{text}")

    with open(output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return output


# ──────────────────────────────────────────────────────────────
# Branding completo
# ──────────────────────────────────────────────────────────────

def apply_branding(clip_path: str, transcript: dict, clip_meta: dict,
                   assets_dir: str = None, output_dir: str = None) -> str:
    """
    Aplica logo, lower third y subtítulos al clip vertical en un solo pass FFmpeg.

    Args:
        clip_path:  ruta al clip vertical (_vertical.mp4)
        transcript: transcript completo {segments, duration}
        clip_meta:  metadatos del clip {start, end, title, ...}
        assets_dir: carpeta de assets (usa ASSETS_DIR del .env o ./assets)
        output_dir: carpeta de salida (usa OUTPUT_DIR del .env o ./output)

    Returns:
        Ruta al clip final con branding aplicado
    """
    assets_dir = assets_dir or os.getenv("ASSETS_DIR", "assets")
    output_dir = output_dir or os.getenv("OUTPUT_DIR", "output")
    os.makedirs(output_dir, exist_ok=True)

    # Nombre del clip de salida basado en el título del clip
    safe_title = "".join(c if c.isalnum() or c in "-_" else "_"
                         for c in clip_meta.get("title", "clip"))[:40]
    basename = os.path.splitext(os.path.basename(clip_path))[0].replace("_vertical", "")
    out = os.path.join(output_dir, f"{basename}_{safe_title}_final.mp4")

    # Generar ASS de subtítulos
    subs_path = clip_path.replace("_vertical.mp4", "_subs.ass").replace("cache/clips/", "cache/")
    create_ass(transcript["segments"], clip_meta["start"], clip_meta["end"], subs_path)

    logo_path        = os.path.join(assets_dir, "logo.png")
    lower_third_path = os.path.join(assets_dir, "lower_third.png")

    has_logo        = os.path.exists(logo_path)
    has_lower_third = os.path.exists(lower_third_path)

    # Construir filtergraph según assets disponibles
    if has_logo and has_lower_third:
        inputs = ["-i", clip_path, "-i", logo_path, "-i", lower_third_path]
        filter_complex = (
            f"[0:v][1:v] overlay=W-w-30:30:format=auto [v1];"
            f"[v1][2:v] overlay=0:H-h-80:format=auto [v2];"
            f"[v2] ass={subs_path} [out]"
        )
    elif has_logo:
        inputs = ["-i", clip_path, "-i", logo_path]
        filter_complex = (
            f"[0:v][1:v] overlay=W-w-30:30:format=auto [v1];"
            f"[v1] ass={subs_path} [out]"
        )
    else:
        # Solo subtítulos
        inputs = ["-i", clip_path]
        filter_complex = f"[0:v] ass={subs_path} [out]"

    cmd = (
        ["ffmpeg"]
        + inputs
        + ["-filter_complex", filter_complex,
           "-map", "[out]", "-map", "0:a",
           "-c:v", "libx264", "-preset", "fast", "-crf", "18",
           "-c:a", "copy",
           "-y", out]
    )
    subprocess.run(cmd, check=True)
    return out
