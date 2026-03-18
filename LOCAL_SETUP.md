# LOCAL SETUP — Entorno Físico y Configuración Local

> Documentación del entorno de desarrollo/producción para el **Video Highlight Pipeline**.

---

## Hardware Objetivo

| Rol | GPU | VRAM | RAM mínima | OS |
|---|---|---|---|---|
| Desarrollo | NVIDIA RTX 3060 | 12 GB | 16 GB | Ubuntu 22.04+ / Windows 11 WSL2 |
| Producción | NVIDIA RTX 5070 | 16 GB | 32 GB | Ubuntu 22.04+ |

> La pipeline **no funciona en CPU** de forma práctica. faster-whisper y Ollama requieren GPU CUDA para tiempos razonables.

---

## Requisitos del Sistema

### Sistema base

| Software | Versión mínima | Instalar |
|---|---|---|
| Python | 3.10+ | `sudo apt install python3.10` |
| pip | 23+ | `python -m ensurepip` |
| FFmpeg | 5.0+ | `sudo apt install ffmpeg` |
| CUDA Toolkit | 11.8+ | Ver sección CUDA |
| cuDNN | 8.x | Incluido con CUDA en Ubuntu |
| Git | cualquiera | `sudo apt install git` |

### CUDA (NVIDIA)

```bash
# Verificar versión CUDA instalada
nvcc --version
nvidia-smi

# Si no está instalado (Ubuntu):
sudo apt install nvidia-cuda-toolkit

# Verificar que Python ve la GPU:
python3 -c "import torch; print(torch.cuda.is_available())"
```

> ⚠️ Si `torch.cuda.is_available()` devuelve `False`, revisar que el driver NVIDIA corresponde a la versión de CUDA.

---

## Instalación de Ollama

Ollama gestiona los modelos LLM localmente como un servicio.

```bash
# 1. Instalar Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Verificar que el servicio está corriendo
ollama list

# 3. Descargar el modelo según hardware:
# --- Desarrollo (RTX 3060, 12GB VRAM) ---
ollama pull mistral:7b     # ~5 GB, recomendado
ollama pull llama3:8b      # ~6 GB, alternativa

# --- Producción (RTX 5070, 16GB+ VRAM) ---
# ollama pull llama3:70b   # ~40 GB — requiere mucha VRAM
# ollama pull mixtral:8x7b # ~26 GB

# 4. Test rápido
ollama run mistral:7b "Responde solo con 'OK'"
```

**Puerto por defecto:** `http://localhost:11434`  
Ollama corre como servicio systemd. Verifica con: `systemctl status ollama`

---

## Instalación del Proyecto

```bash
# 1. Clonar el repositorio
git clone <URL_DEL_REPO> highlight_pipeline
cd highlight_pipeline

# 2. Crear entorno virtual
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# 3. Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# 4. Copiar y editar variables de entorno
cp .env.example .env
nano .env   # (o tu editor favorito)
```

---

## Variables de Entorno (`.env`)

```env
# ── Modelos ──────────────────────────────────────
OLLAMA_MODEL=mistral:7b          # RTX 3060
# OLLAMA_MODEL=llama3:70b        # RTX 5070 (descomenta para producción)

WHISPER_MODEL=medium             # RTX 3060
# WHISPER_MODEL=large-v2         # RTX 5070

WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=int8        # RTX 3060 (ahorra VRAM)
# WHISPER_COMPUTE_TYPE=float16   # RTX 5070

# ── Paralelización ───────────────────────────────
MAX_WORKERS=2                    # RTX 3060
# MAX_WORKERS=5                  # RTX 5070

# ── Branding del canal ───────────────────────────
STREAMER_NAME=NombreDelStreamer
CHANNEL_HANDLE=@tucanal

# ── Paths ────────────────────────────────────────
CACHE_DIR=./cache
OUTPUT_DIR=./output
ASSETS_DIR=./assets
```

---

## Configuración por Hardware (resumen rápido)

### RTX 3060 — Desarrollo

| Parámetro | Valor |
|---|---|
| `WHISPER_MODEL` | `medium` |
| `WHISPER_COMPUTE_TYPE` | `int8` |
| `OLLAMA_MODEL` | `mistral:7b` |
| `MAX_WORKERS` | `2` |
| Tiempo transcripción ~1h vídeo | ~8–12 min |

### RTX 5070 — Producción

| Parámetro | Valor |
|---|---|
| `WHISPER_MODEL` | `large-v2` |
| `WHISPER_COMPUTE_TYPE` | `float16` |
| `OLLAMA_MODEL` | `llama3:70b` |
| `MAX_WORKERS` | `4–6` |
| Tiempo transcripción ~1h vídeo | ~3–5 min |

> Para pasar de dev a producción **solo hay que cambiar el `.env`**. El código no cambia.

---

## Verificar que Todo Funciona

```bash
# 1. GPU disponible
python3 -c "from faster_whisper import WhisperModel; m = WhisperModel('tiny', device='cuda'); print('faster-whisper OK')"

# 2. Ollama responde
curl http://localhost:11434/api/tags

# 3. FFmpeg disponible
ffmpeg -version | head -1

# 4. mediapipe (para reencuadre con detección facial)
python3 -c "import mediapipe; print('mediapipe OK')"

# 5. Lanzar la UI
python app.py
# → Abrir http://localhost:7860
```

---

## Estructura de Carpetas Esperada

```
highlight_pipeline/
├── .env                   ← No subir a git (en .gitignore)
├── app.py
├── requirements.txt
├── LOCAL_SETUP.md         ← Este archivo
├── pipeline/
│   ├── audio.py
│   ├── transcribe.py
│   ├── llm.py
│   ├── validate.py        ← CRÍTICO
│   ├── cutter.py
│   ├── reframe.py
│   └── brand.py
├── prompts/
│   ├── gaming.txt
│   └── podcast.txt
├── assets/
│   ├── logo.png           ← Tu logo (PNG con canal alpha)
│   └── lower_third.png    ← Plantilla lower third (PNG con alpha)
├── cache/                 ← Generado automáticamente (gitignore)
│   ├── audio.wav
│   ├── transcript.json
│   ├── candidates.json
│   └── validated.json
└── output/                ← Clips finales (gitignore)
```

---

## Notas de Rendimiento

- **VRAM RTX 3060:** Whisper `medium` + Ollama `mistral:7b` caben juntos si no corren en paralelo. El pipeline los ejecuta secuencialmente, por lo que no hay conflicto.
- **RAM del sistema:** La transcripción de un vídeo de 2h puede generar transcripts de ~500 KB. No es crítico.
- **Disco:** Reservar al menos **20 GB** para `cache/` (audio WAV de vídeos largos puede pesar varios GB).
- **El proceso más lento es la transcripción.** El sistema de caché guarda `transcript.json` para no repetirla si el pipeline se interrumpe.

---

## Problemas Comunes

| Problema | Solución |
|---|---|
| `CUDA out of memory` en Whisper | Bajar a `compute_type='int8'`, reducir `batch_size` |
| Ollama no responde | `systemctl restart ollama` |
| FFmpeg no encontrado | `sudo apt install ffmpeg` |
| mediapipe crash | `pip install mediapipe==0.10.x` (evitar versiones muy nuevas) |
| `libcuda.so` no encontrado | Reinstalar driver NVIDIA o añadir al LD_LIBRARY_PATH |

---

*Última actualización: Marzo 2026*
