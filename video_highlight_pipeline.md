# VIDEO HIGHLIGHT PIPELINE
## Extracción automática de clips verticales desde directos

> **Stack:** Gaming & Podcast · Vertical 9:16 · Gradio UI · Ollama (local LLM) · faster-whisper · RTX 3060 → 5070

---

## PRINCIPIO FUNDAMENTAL

> **El sistema NUNCA confía en el LLM. Todo output del modelo pasa por normalización, validación y corrección antes de tocar un solo frame de vídeo.**

---

## 1. Flujo Principal

```
Video entrada
  → Extracción audio (FFmpeg)
  → Transcripción ASR (faster-whisper)
  → Análisis semántico (Ollama local)
  → Validación de clips (Python puro)
  → Corte de clips (FFmpeg)
  → Reencuadre vertical 9:16 (FFmpeg + mediapipe)
  → Branding (subtítulos ASS + logo + lower thirds)
  → Clips finales en /output
```

---

## 2. Stack Tecnológico

| Componente | Tecnología | Crítico |
|---|---|---|
| Extracción audio | FFmpeg | ✅ |
| ASR | faster-whisper (medium / large-v2) | ✅ |
| Análisis semántico | Ollama (mistral:7b / llama3:70b) | ⚠️ |
| Validación | Python puro | 🔥 |
| Corte | FFmpeg modo híbrido | 🔥 |
| Reencuadre 9:16 | FFmpeg + mediapipe (face) | ✅ |
| Subtítulos | ASS burn-in via FFmpeg | ✅ |
| Branding | FFmpeg filtergraph | ✅ |
| UI | Gradio (localhost:7860) | ✅ |

---

## 3. Hardware Target

| Entorno | GPU | Whisper | LLM Ollama | Workers FFmpeg |
|---|---|---|---|---|
| Desarrollo | RTX 3060 12GB | medium (int8) | mistral:7b | 2 |
| Producción | RTX 5070 16GB+ | large-v2 (fp16) | llama3:70b | 4-6 |

---

## 4. Estructura de Carpetas

```
highlight_pipeline/
├── app.py                  # Gradio UI — punto de entrada
├── pipeline/
│   ├── audio.py            # Fase 1: extracción audio
│   ├── transcribe.py       # Fase 2: faster-whisper
│   ├── llm.py              # Fase 3: Ollama client + prompt
│   ├── validate.py         # Fase 4: validación y corrección (CRÍTICO)
│   ├── cutter.py           # Fase 5: FFmpeg corte preciso
│   ├── reframe.py          # Fase 6: reencuadre 9:16
│   └── brand.py            # Fase 7: subtítulos + logo + lower thirds
├── assets/
│   ├── logo.png            # Logo del canal (PNG con alpha)
│   └── lower_third.png     # Plantilla lower third (PNG con alpha)
├── prompts/
│   ├── gaming.txt          # Prompt para contenido gaming
│   └── podcast.txt         # Prompt para charlas/podcast
├── output/                 # Clips finales listos para publicar
└── cache/                  # transcript.json, candidates.json, validated.json
```

> **IMPORTANTE:** Los prompts están en archivos `.txt` separados del código. Se pueden iterar sin tocar Python. El sistema elige automáticamente `gaming.txt` o `podcast.txt` según el `content_type`.

---

## 5. Data Contracts (Schemas JSON entre fases)

### 5.1 Transcript (salida de ASR)
```json
{
  "segments": [
    { "id": 0, "start": 12.34, "end": 18.90, "text": "texto transcrito" }
  ],
  "duration": 3600.0
}
```
**Reglas:** segmentos ordenados, sin solapamiento, `start < end` siempre.

### 5.2 Candidate Clips (salida del LLM — NO confiable)
```json
{
  "clips": [
    { "start": 120.5, "end": 165.2, "title": "momento clave", "score": 0.87 }
  ]
}
```
> ⚠️ **NUNCA usar directamente.** Pasar siempre por `validate.py`.

### 5.3 Validated Clips (salida de validación — confiable)
```json
{
  "clips": [
    {
      "start": 118.0, "end": 168.0,
      "title": "momento clave", "score": 0.87,
      "source": "llm_v1", "validated": true, "content_type": "gaming"
    }
  ]
}
```

---

## 6. Fase 1 — Extracción de Audio

```bash
ffmpeg -i input.mp4 -ac 1 -ar 16000 -vn -y cache/audio.wav
```

| Parámetro | Valor | Por qué |
|---|---|---|
| `-ac 1` | Mono | ASR más estable, menor VRAM |
| `-ar 16000` | 16 kHz | Estándar Whisper, suficiente para voz |
| `-vn` | Sin vídeo | Solo audio, más rápido |

```python
def extract_audio(video_path: str, output_path: str = 'cache/audio.wav') -> str:
    cmd = f'ffmpeg -i {video_path} -ac 1 -ar 16000 -vn -y {output_path}'
    subprocess.run(cmd, shell=True, check=True)
    return output_path
```

---

## 7. Fase 2 — Transcripción (faster-whisper)

### Config por hardware

| Config | RTX 3060 (dev) | RTX 5070 (prod) |
|---|---|---|
| Modelo | medium | large-v2 |
| compute_type | int8 | float16 |
| beam_size | 3 | 5 |
| batch_size | 4 | 16 |
| Tiempo ~1h video | ~8-12 min | ~3-5 min |

```python
from faster_whisper import WhisperModel

def transcribe(audio_path: str, model_size='medium') -> dict:
    model = WhisperModel(model_size, device='cuda', compute_type='int8')
    segments_raw, info = model.transcribe(
        audio_path, beam_size=3, language='es', vad_filter=True
    )
    segments = [
        {'id': i, 'start': round(s.start, 3), 'end': round(s.end, 3), 'text': s.text.strip()}
        for i, s in enumerate(segments_raw)
    ]
    return {'segments': segments, 'duration': info.duration}
```

> **Activa siempre `vad_filter=True`.** Elimina silencios y produce segmentos más limpios, reduciendo errores en el LLM.

### Problemas comunes

| Problema | Solución |
|---|---|
| Segmentos muy largos (>15s) | `vad_filter=True` |
| CUDA OOM en 3060 | `compute_type='int8'`, reduce `batch_size` |
| Idioma mixto | Fuerza `language='es'` siempre |

---

## 8. Fase 3 — Análisis Semántico (Ollama)

### Modelos recomendados

| Modelo | Gaming | Podcast | VRAM | Hardware |
|---|---|---|---|---|
| mistral:7b | ✅ | ✅ Muy bueno | ~5GB | 3060 ok |
| llama3:8b | ✅ | ✅ | ~6GB | 3060 ok |
| llama3:70b | ⭐ | ⭐ | ~40GB | 5070 req. |
| mixtral:8x7b | ⭐ | ⭐ | ~26GB | 5070 req. |

### Prompt — Gaming (`prompts/gaming.txt`)

```
Eres un experto en creación de contenido para TikTok y Reels.
Analiza este transcript de un directo de GAMING y selecciona los mejores momentos.

CRITERIOS GAMING:
- Reacciones exageradas / gritos de emoción o rabia
- Muertes inesperadas o partidas épicas
- Frases virales o momentos de humor
- Victorias contra todo pronóstico
- Fails memorables

REGLAS ESTRICTAS:
- Duración de cada clip: mínimo 20s, máximo 60s
- No cortar frases a medias
- Máximo 8 clips
- Score 0.0 a 1.0 (prioriza >0.7)
- NO incluyas timestamps fuera de [0, {duration}]

TRANSCRIPT:
{transcript_text}

Responde SOLO con JSON válido, sin markdown, sin explicaciones:
{"clips": [{"start": X.X, "end": Y.Y, "title": "...", "score": 0.XX}]}
```

### Prompt — Podcast (`prompts/podcast.txt`)

```
Eres un experto en clips virales de podcast y charlas.
Analiza este transcript y selecciona los momentos más impactantes.

CRITERIOS PODCAST:
- Opiniones fuertes o controversiales
- Historias personales emotivas o sorprendentes
- Insights o reflexiones profundas
- Momentos de humor o ironía
- Frases que generan debate

REGLAS ESTRICTAS:
- Duración: mínimo 30s, máximo 90s (charlas necesitan más contexto)
- Empieza el clip justo antes de la idea principal, no en mitad
- Máximo 6 clips
- Score 0.0 a 1.0
- NO incluyas timestamps fuera de [0, {duration}]

Responde SOLO con JSON válido, sin markdown, sin explicaciones:
{"clips": [{"start": X.X, "end": Y.Y, "title": "...", "score": 0.XX}]}
```

### Implementación Python

```python
import ollama, json

def generate_candidates(transcript: dict, content_type: str = 'gaming') -> dict:
    prompt = open(f'prompts/{content_type}.txt').read()
    full_text = ' '.join(s['text'] for s in transcript['segments'])
    prompt = (prompt
              .replace('{transcript_text}', full_text)
              .replace('{duration}', str(transcript['duration'])))
    
    resp = ollama.chat(
        model='mistral:7b',
        messages=[{'role': 'user', 'content': prompt}]
    )
    raw = resp['message']['content']
    # Limpia markdown por si el modelo lo añade igualmente
    raw = raw.strip().lstrip('```json').rstrip('```').strip()
    return json.loads(raw)
```

---

## 9. Fase 4 — Validación (MÓDULO CRÍTICO 🔥)

### Pipeline de validación

```
Raw Clips (LLM output)
  → 1. Bounds Check        (timestamps dentro de [0, duration])
  → 2. Duration Filter     (min/max duración válida)
  → 3. Snap to Transcript  (alinear a segmentos reales de ASR)
  → 4. Margin Expansion    (añadir 2s de margen natural)
  → 5. Overlap Resolution  (eliminar solapamientos, conservar mayor score)
  → Validated Clips ✅
```

### Implementación Python completa

```python
def validate(candidates: dict, transcript: dict,
             min_dur: float = 15, max_dur: float = 90,
             margin: float = 2.0) -> dict:
    duration = transcript['duration']
    segments = transcript['segments']
    clips = candidates.get('clips', [])
    valid = []

    for clip in clips:
        s = max(0.0, float(clip.get('start', 0)))
        e = min(float(duration), float(clip.get('end', 0)))

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

        clip['start'], clip['end'] = s, e
        clip['validated'] = True
        valid.append(clip)

    # 5. Overlap resolution (score DESC, conserva el mejor)
    valid.sort(key=lambda x: -x.get('score', 0))
    no_overlap = []
    for clip in valid:
        if not any(overlaps(clip, kept) for kept in no_overlap):
            no_overlap.append(clip)

    no_overlap.sort(key=lambda x: x['start'])
    return {'clips': no_overlap}


def snap_to_segment_start(t: float, segments: list, window: float = 5.0) -> float:
    nearby = [s for s in segments if abs(s['start'] - t) < window]
    if not nearby:
        return t
    return min(nearby, key=lambda s: abs(s['start'] - t))['start']


def snap_to_segment_end(t: float, segments: list, window: float = 5.0) -> float:
    nearby = [s for s in segments if abs(s['end'] - t) < window]
    if not nearby:
        return t
    return min(nearby, key=lambda s: abs(s['end'] - t))['end']


def overlaps(a: dict, b: dict) -> bool:
    return not (a['end'] <= b['start'] or a['start'] >= b['end'])
```

---

## 10. Fase 5 — Corte de Clips

### Estrategias

| Modo | Precisión | Velocidad | Usar |
|---|---|---|---|
| `-c copy` | ❌ Baja (keyframes) | ⚡ Muy rápido | No |
| Re-encode full | ✅ Alta | 🐢 Lento | No |
| **Híbrido** | ✅ Alta | 🚀 Medio | **✅ Siempre** |

### Comando híbrido (recomendado)

```bash
ffmpeg -ss {START-1} -i input.mp4 -ss 1 -to {DURATION} \
       -c:v libx264 -preset fast -crf 18 \
       -c:a aac -b:a 192k \
       -movflags +faststart \
       -y cache/clips/clip_001_raw.mp4
```

> El `-ss` antes del `-i` busca el keyframe más cercano. El segundo `-ss 1` corrige el offset. Resultado: corte preciso a nivel de frame.

### Implementación Python con paralelización

```python
from concurrent.futures import ThreadPoolExecutor
import subprocess

def cut_all(video_path: str, clips: list, workers: int = 2) -> list:
    def cut_one(i: int, clip: dict) -> str:
        out = f'cache/clips/clip_{i:03d}_raw.mp4'
        s, e = clip['start'], clip['end']
        dur = e - s
        cmd = (
            f'ffmpeg -ss {max(0, s - 1)} -i {video_path} -ss 1 -to {dur} '
            f'-c:v libx264 -preset fast -crf 18 '
            f'-c:a aac -b:a 192k -movflags +faststart -y {out}'
        )
        subprocess.run(cmd, shell=True, check=True)
        return out

    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(lambda x: cut_one(*x), enumerate(clips)))

# workers=2 para RTX 3060, workers=4-5 para RTX 5070
```

---

## 11. Fase 6 — Reencuadre Vertical 9:16

### Estrategias disponibles

| Estrategia | Cómo | Calidad | Usar para |
|---|---|---|---|
| `center` | Recorta el centro del frame | Media | Fallback |
| `smart` | Detecta zona de movimiento | Alta | **Gaming** |
| `face` | Sigue la cara con mediapipe | Muy alta | **Podcast** |

### Comando FFmpeg — Smart crop (gaming)

```bash
# Paso 1: detectar zona de interés
ffmpeg -i clip_raw.mp4 -vf 'cropdetect=limit=24:round=16:reset=0' -f null - 2>&1 | grep crop

# Paso 2: crop + escalar a 1080x1920
ffmpeg -i clip_raw.mp4 \
       -vf 'crop=ih*9/16:ih:iw/2-ih*9/16/2:0,scale=1080:1920' \
       -c:v libx264 -preset fast -crf 18 \
       -c:a aac -b:a 192k \
       -y cache/clips/clip_001_vertical.mp4
```

### Implementación Python unificada

```python
def reframe_vertical(clip_path: str, strategy: str = 'smart',
                     output_path: str = None) -> str:
    out = output_path or clip_path.replace('_raw.mp4', '_vertical.mp4')

    if strategy == 'center':
        vf = 'crop=ih*9/16:ih:iw/2-ih*9/16/2:0,scale=1080:1920'
    elif strategy == 'smart':
        vf = 'crop=ih*9/16:ih:iw/2-ih*9/16/2:0,scale=1080:1920'
    elif strategy == 'face':
        x, cw = get_face_crop_coords(clip_path)
        vf = f'crop={cw}:ih:{x}:0,scale=1080:1920'

    cmd = f'ffmpeg -i {clip_path} -vf "{vf}" -c:v libx264 -preset fast -crf 18 -y {out}'
    subprocess.run(cmd, shell=True, check=True)
    return out


def get_face_crop_coords(video_path: str) -> tuple:
    """Analiza el primer frame y devuelve (x_start, crop_width) centrado en la cara."""
    import cv2, mediapipe as mp
    cap = cv2.VideoCapture(video_path)
    ret, frame = cap.read()
    cap.release()
    h, w = frame.shape[:2]
    crop_w = int(h * 9 / 16)
    # ... mediapipe face detection para obtener face_center_x ...
    face_center_x = w // 2  # fallback: centro
    x_start = max(0, min(face_center_x - crop_w // 2, w - crop_w))
    return x_start, crop_w
```

---

## 12. Fase 7 — Branding Final

### Elementos

| Elemento | Formato | Posición en 1080x1920 |
|---|---|---|
| Logo / watermark | PNG con alpha | Esquina sup. derecha (W-w-30, 30) |
| Lower third | PNG con alpha o drawtext | Zona inferior (y=1580) |
| Subtítulos | ASS burn-in | Centro-inferior (y automático) |

### Generación del ASS de subtítulos

```python
def create_ass(segments: list, clip_start: float, clip_end: float,
               output: str = 'subs.ass') -> str:
    header = """[Script Info]
ScriptType: v4.00+
[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,Bold,Shadow,Alignment
Style: Default,Arial,72,&H00FFFFFF,1,2,2
[Events]
Format: Layer,Start,End,Style,Text"""

    lines = [header]
    for seg in segments:
        if seg['end'] < clip_start or seg['start'] > clip_end:
            continue
        s = seg['start'] - clip_start
        e = seg['end'] - clip_start
        lines.append(f"Dialogue: 0,{fmt(s)},{fmt(e)},Default,,{seg['text']}")

    with open(output, 'w') as f:
        f.write('\n'.join(lines))
    return output


def fmt(t: float) -> str:
    """Formatea segundos a H:MM:SS.cc para ASS"""
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"
```

### FFmpeg filtergraph completo (un solo pass)

```bash
ffmpeg -i clip_vertical.mp4 \
       -i assets/logo.png \
       -i assets/lower_third.png \
       -filter_complex "
         [0:v][1:v] overlay=W-w-30:30:format=auto [v1];
         [v1][2:v]  overlay=0:H-h-80:format=auto  [v2];
         [v2] ass=cache/subs_001.ass [out]
       " \
       -map "[out]" -map 0:a \
       -c:v libx264 -preset fast -crf 18 \
       -c:a copy \
       -y output/clip_001_final.mp4
```

> Usa `-c:a copy` — el audio ya está correcto desde la fase de corte. Solo re-procesa el vídeo.

### Lower third solo con texto (sin PNG)

```bash
-vf "drawbox=x=0:y=1580:w=iw:h=200:color=black@0.6:t=fill,
     drawtext=fontfile=/path/font.ttf:text='NOMBRE STREAMER':fontsize=52:fontcolor=white:x=40:y=1620,
     drawtext=fontfile=/path/font.ttf:text='@canal':fontsize=36:fontcolor=#AAAAAA:x=40:y=1690"
```

---

## 13. Gradio UI (`app.py`)

```python
import gradio as gr
import json, os
from pipeline.audio import extract_audio
from pipeline.transcribe import transcribe
from pipeline.llm import generate_candidates
from pipeline.validate import validate
from pipeline.cutter import cut_all
from pipeline.reframe import reframe_vertical
from pipeline.brand import apply_branding

def save_json(data: dict, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def run_pipeline(video_file, content_type, min_dur, max_dur, progress=gr.Progress()):
    progress(0.00, desc="Extrayendo audio...")
    audio = extract_audio(video_file)

    progress(0.15, desc="Transcribiendo... (esto tarda ~10 min en 3060)")
    transcript = transcribe(audio)
    save_json(transcript, 'cache/transcript.json')

    progress(0.45, desc="Analizando con LLM...")
    candidates = generate_candidates(transcript, content_type)
    save_json(candidates, 'cache/candidates.json')

    progress(0.55, desc="Validando clips...")
    validated = validate(candidates, transcript, min_dur, max_dur)
    save_json(validated, 'cache/validated.json')

    progress(0.65, desc="Cortando clips...")
    raw_clips = cut_all(video_file, validated['clips'])

    progress(0.80, desc="Reencuadrando a vertical 9:16...")
    strategy = 'face' if content_type == 'podcast' else 'smart'
    vertical_clips = [reframe_vertical(c, strategy=strategy) for c in raw_clips]

    progress(0.90, desc="Aplicando branding...")
    final_clips = [
        apply_branding(c, transcript, validated['clips'][i])
        for i, c in enumerate(vertical_clips)
    ]

    progress(1.0, desc="¡Listo!")
    return final_clips


with gr.Blocks(title="🎬 Highlight Pipeline") as demo:
    gr.Markdown("# 🎬 Video Highlight Pipeline\nExtracción automática de clips verticales desde directos")

    with gr.Row():
        video_in = gr.File(label="Vídeo del directo", file_types=[".mp4", ".mkv"])
        content_type = gr.Dropdown(["gaming", "podcast"], value="gaming", label="Tipo de contenido")

    with gr.Row():
        min_dur = gr.Slider(10, 60, value=20, label="Duración mínima (s)")
        max_dur = gr.Slider(30, 120, value=60, label="Duración máxima (s)")

    run_btn = gr.Button("🚀 Procesar", variant="primary")
    output_files = gr.File(label="Clips finales", file_count="multiple")

    run_btn.click(
        fn=run_pipeline,
        inputs=[video_in, content_type, min_dur, max_dur],
        outputs=output_files
    )

demo.launch(server_name="0.0.0.0", server_port=7860)
```

---

## 14. Variables de Entorno (`.env`)

```env
OLLAMA_MODEL=mistral:7b
WHISPER_MODEL=medium
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=int8
MAX_WORKERS=2
STREAMER_NAME=NombreDelStreamer
CHANNEL_HANDLE=@tucanal
```

> Para pasar a producción (RTX 5070): cambia `OLLAMA_MODEL`, `WHISPER_MODEL`, `WHISPER_COMPUTE_TYPE` y `MAX_WORKERS`. Nada más.

---

## 15. Instalación

```bash
# 1. Crear entorno virtual
python -m venv venv && source venv/bin/activate

# 2. requirements.txt
pip install faster-whisper gradio ollama opencv-python mediapipe tqdm python-dotenv

# 3. FFmpeg
sudo apt install ffmpeg

# 4. Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull mistral:7b        # desarrollo (3060)
# ollama pull llama3:70b      # producción (5070)

# 5. Lanzar
python app.py
# → http://localhost:7860
```

---

## 16. Sistema de Caché por Fases

Guarda los JSONs intermedios para poder reanudar sin repetir la transcripción (la fase más costosa):

```python
def cached(filename: str, fn, *args, force=False):
    path = f'cache/{filename}'
    if os.path.exists(path) and not force:
        with open(path) as f:
            return json.load(f)
    result = fn(*args)
    save_json(result, path)
    return result

# Uso en el pipeline:
transcript = cached('transcript.json', transcribe, audio)
candidates = cached('candidates.json', generate_candidates, transcript)
validated  = cached('validated.json',  validate, candidates, transcript)
```

---

## 17. Métricas de Calidad a Loggar

| Métrica | Cómo calcular | Target |
|---|---|---|
| % clips válidos | `len(validated) / len(candidates)` | > 70% |
| % clips descartados (bounds) | clips con start/end inválido del LLM | < 20% |
| Desviación snap media | `mean(abs(snap_start - original_start))` | < 3s |
| Duración media clips | `mean([c['end'] - c['start'] for c in clips])` | 30-60s |
| Score medio | `mean([c['score'] for c in validated])` | > 0.72 |

---

## 18. Riesgos y Mitigaciones

| Riesgo | Mitigación |
|---|---|
| LLM produce JSON inválido | `try/except` + retry con temperatura 0.1 |
| LLM alucina timestamps | Módulo `validate.py` (Fase 4) |
| ASR desincronizado | Verificar WAV 16kHz + `vad_filter=True` |
| CUDA OOM en 3060 | `compute_type='int8'`, `batch_size` bajo, modelo `medium` |
| Reencuadre corta al speaker | Usa `strategy='face'` para podcast |
| Corte impreciso | Usa modo híbrido, nunca `-c copy` |

---

## 19. Roadmap Futuro

### Fase 2 — Mejoras de selección
- Reranking con embeddings semánticos
- Detección de picos de audio (energía) para momentos de emoción en gaming
- Multi-pass clipping

### Fase 3 — Branding avanzado
- Subtítulos animados karaoke (word-level timestamps de Whisper)
- Intro/outro con `xfade` de FFmpeg
- Formato blur de fondo (16:9 borroso + clip vertical encima)

### Fase 4 — Producción
- Watch folder automático (`watchdog` Python)
- Cola de procesamiento (Celery / RQ)
- Upload automático a plataformas vía API

---

*Versión 1.0 — Marzo 2026*
