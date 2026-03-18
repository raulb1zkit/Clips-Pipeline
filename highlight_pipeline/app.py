"""
app.py — Punto de entrada del Video Highlight Pipeline.
UI Gradio en http://localhost:7860
"""
import os
import json
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

from pipeline.audio import extract_audio
from pipeline.transcribe import transcribe
from pipeline.llm import generate_candidates
from pipeline.validate import validate
from pipeline.cutter import cut_all
from pipeline.reframe import reframe_vertical
from pipeline.brand import apply_branding


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────

def _save_json(data: dict, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _cached(filename: str, fn, *args, force: bool = False):
    """Carga el JSON cacheado si existe; si no, ejecuta fn y guarda el resultado."""
    path = os.path.join(os.getenv("CACHE_DIR", "cache"), filename)
    if os.path.exists(path) and not force:
        print(f"[cache] Usando {path}")
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    result = fn(*args)
    _save_json(result, path)
    return result


# ──────────────────────────────────────────────────────────────
# Pipeline principal
# ──────────────────────────────────────────────────────────────

def run_pipeline(video_file, content_type, llm_provider,
                 min_dur, max_dur, force_retranscribe,
                 progress=gr.Progress()):

    if video_file is None:
        return [], "❌ Sube un vídeo primero."

    video_path = video_file.name
    provider = "local" if llm_provider == "Local (Ollama)" else "minimax"

    # Fase 1 — Extracción de audio
    progress(0.05, desc="Extrayendo audio...")
    audio_path = extract_audio(video_path)

    # Fase 2 — Transcripción (cacheada)
    progress(0.15, desc="Transcribiendo... (puede tardar varios minutos)")
    transcript = _cached(
        "transcript.json",
        lambda: transcribe(audio_path),
        force=force_retranscribe,
    )

    # Fase 3 — Análisis LLM
    progress(0.45, desc=f"Analizando con {llm_provider}...")
    candidates = generate_candidates(transcript, content_type, provider=provider)
    _save_json(candidates, os.path.join(os.getenv("CACHE_DIR", "cache"), "candidates.json"))

    # Fase 4 — Validación
    progress(0.55, desc="Validando clips...")
    validated = validate(candidates, transcript, min_dur=float(min_dur), max_dur=float(max_dur))
    _save_json(validated, os.path.join(os.getenv("CACHE_DIR", "cache"), "validated.json"))

    n_valid = len(validated["clips"])
    if n_valid == 0:
        return [], "⚠️ El LLM no generó clips válidos. Prueba con otro modelo o tipo de contenido."

    # Fase 5 — Corte
    progress(0.65, desc=f"Cortando {n_valid} clips...")
    raw_clips = cut_all(video_path, validated["clips"])

    # Fase 6 — Reencuadre
    progress(0.80, desc="Reencuadrando a 9:16 vertical...")
    strategy = "face" if content_type == "podcast" else "smart"
    vertical_clips = [reframe_vertical(c, strategy=strategy) for c in raw_clips]

    # Fase 7 — Branding
    progress(0.90, desc="Aplicando branding...")
    final_clips = [
        apply_branding(c, transcript, validated["clips"][i])
        for i, c in enumerate(vertical_clips)
    ]

    progress(1.0, desc="¡Listo!")
    summary = (
        f"✅ {n_valid} clips generados.\n"
        f"Provider: {llm_provider} | Contenido: {content_type}"
    )
    return final_clips, summary


# ──────────────────────────────────────────────────────────────
# Gradio UI
# ──────────────────────────────────────────────────────────────

with gr.Blocks(title="🎬 Highlight Pipeline") as demo:
    gr.Markdown(
        "# 🎬 Video Highlight Pipeline\n"
        "Extracción automática de clips verticales 9:16 desde directos de gaming y podcast."
    )

    with gr.Row():
        with gr.Column():
            video_in = gr.File(
                label="Vídeo del directo",
                file_types=[".mp4", ".mkv", ".mov"]
            )
            content_type = gr.Dropdown(
                choices=["gaming", "podcast"],
                value="gaming",
                label="Tipo de contenido"
            )
            llm_provider = gr.Dropdown(
                choices=["Local (Ollama)", "MiniMax-M2.5 (Cloud)"],
                value="Local (Ollama)",
                label="Proveedor LLM"
            )

        with gr.Column():
            min_dur = gr.Slider(10, 60,  value=20, step=5, label="Duración mínima (s)")
            max_dur = gr.Slider(30, 120, value=60, step=5, label="Duración máxima (s)")
            force_retranscribe = gr.Checkbox(
                label="Forzar re-transcripción (ignora caché)",
                value=False
            )

    run_btn   = gr.Button("🚀 Procesar", variant="primary")
    status_md = gr.Markdown("")
    output_files = gr.File(label="Clips finales", file_count="multiple")

    run_btn.click(
        fn=run_pipeline,
        inputs=[video_in, content_type, llm_provider, min_dur, max_dur, force_retranscribe],
        outputs=[output_files, status_md]
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
