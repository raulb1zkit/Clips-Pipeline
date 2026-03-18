# 🎬 Video Highlight Pipeline

Extracción automática de clips verticales 9:16 desde directos de gaming y podcast.

> **Stack:** FFmpeg · faster-whisper · Ollama (local) / MiniMax-M2.5 (cloud) · mediapipe · Gradio

---

## Flujo

```
Vídeo entrada
  → Extracción audio (FFmpeg)
  → Transcripción ASR (faster-whisper)
  → Análisis semántico (Ollama local ó MiniMax-M2.5 cloud)
  → Validación de clips (Python puro)  ← punto crítico, nunca salta
  → Corte de clips (FFmpeg modo híbrido)
  → Reencuadre vertical 9:16 (FFmpeg + mediapipe)
  → Branding (subtítulos ASS + logo + lower third)
  → Clips finales en /output
```

---

## Requisitos del sistema

| Software | Instalación |
|---|---|
| Python 3.10+ | `sudo apt install python3.10` |
| FFmpeg 5+ | `sudo apt install ffmpeg` |
| CUDA 11.8+ | Via driver NVIDIA |
| Ollama | `curl -fsSL https://ollama.com/install.sh \| sh` |

### Hardware objetivo

| Rol | GPU | VRAM |
|---|---|---|
| Desarrollo | RTX 3060 | 12 GB |
| Producción | RTX 5070 | 16 GB+ |

---

## Instalación

```bash
# 1. Clonar e instalar
git clone <repo-url> highlight_pipeline
cd highlight_pipeline
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configurar entorno
cp .env.example .env
# Editar .env con tus valores

# 3. Descargar modelo Ollama (si usas provider local)
ollama pull mistral:7b      # RTX 3060 (dev)
# ollama pull llama3:70b   # RTX 5070 (prod)

# 4. Lanzar
python app.py
# → http://localhost:7860
```

---

## Configuración (`.env`)

```env
# Provider LLM: local | minimax
LLM_PROVIDER=local

# Si usas MiniMax-M2.5 (cloud)
MINIMAX_API_KEY=
MINIMAX_MODEL=MiniMax-M2.5

# Whisper — dev: medium/int8 | prod: large-v2/float16
WHISPER_MODEL=medium
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=int8

# Paralelización FFmpeg — dev: 2 | prod: 4-6
MAX_WORKERS=2

# Branding
STREAMER_NAME=NombreDelStreamer
CHANNEL_HANDLE=@tucanal
```

Para pasar de desarrollo (RTX 3060) a producción (RTX 5070): **cambia 4 líneas del `.env`**, nada más.

---

## Estructura del proyecto

```
highlight_pipeline/
├── app.py                  # Punto de entrada — Gradio UI
├── pipeline/
│   ├── audio.py            # Fase 1: extracción audio
│   ├── transcribe.py       # Fase 2: faster-whisper
│   ├── llm/
│   │   ├── __init__.py     # generate_candidates() — interfaz única
│   │   ├── base.py         # LLMProvider abstracto + retry
│   │   ├── local.py        # OllamaProvider
│   │   └── cloud.py        # MiniMaxProvider (MiniMax-M2.5)
│   ├── validate.py         # Fase 4: validación 🔥 (CRÍTICO)
│   ├── cutter.py           # Fase 5: corte FFmpeg híbrido
│   ├── reframe.py          # Fase 6: reencuadre 9:16
│   └── brand.py            # Fase 7: subtítulos + logo + lower third
├── prompts/
│   ├── gaming.txt          # Prompt gaming (editable sin tocar código)
│   └── podcast.txt         # Prompt podcast
├── assets/
│   ├── logo.png            # Logo canal (PNG con alpha)
│   └── lower_third.png     # Lower third (PNG con alpha) — opcional
├── output/                 # Clips finales (gitignored)
├── cache/                  # JSONs y audio intermedios (gitignored)
├── requirements.txt
└── .env.example
```

---

## Providers LLM

El análisis semántico (Fase 3) soporta dos backends intercambiables:

| Provider | Configuración | Requiere internet |
|---|---|---|
| **Local (Ollama)** | `LLM_PROVIDER=local` | ❌ No |
| **MiniMax-M2.5** | `LLM_PROVIDER=minimax` + API key | ✅ Sí |

El resto del pipeline (Whisper, FFmpeg, validación, corte, branding) es siempre **100% local**.

---

## Tiempos estimados (vídeo de 1h)

| Hardware | Transcripción | Análisis LLM | Corte + branding |
|---|---|---|---|
| RTX 3060 (dev) | ~8–12 min | ~1–2 min | ~5–10 min |
| RTX 5070 (prod) | ~3–5 min | ~1 min | ~2–4 min |

> La transcripción se cachea en `cache/transcript.json`. Si el pipeline falla en fases posteriores, no se repite.

---

## Assets opcionales

Coloca tus archivos en `/assets/`:
- `logo.png` — PNG con canal alpha (ej. 300×300px)
- `lower_third.png` — PNG con canal alpha (ej. 1080×200px)

Si no existen, el pipeline aplica solo subtítulos y continúa sin errores.

---

## Principio de diseño

> **El sistema NUNCA confía en el LLM.** Todo output del modelo pasa por `validate.py` antes de tocar un solo frame de vídeo.

---

*Versión 1.0 — Marzo 2026*
