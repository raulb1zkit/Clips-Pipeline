# Video Highlight Pipeline Architecture

Automated extraction of vertical clips from long-form streams.

> **Stack:** Gaming & Podcast · Vertical 9:16 · Gradio UI · Ollama (local LLM) · faster-whisper · FFmpeg

---

## 🏗️ Core Principles

> **Zero-Trust AI Output:** The system never assumes the LLM's output is perfect. Every generated clip passes through a normalization, validation, and correction layer before any video frames are processed.

---

## 1. Main Workflow

```text
Input Video
  → Audio Extraction (FFmpeg)
  → ASR Transcription (faster-whisper)
  → Semantic Analysis (Ollama local / Cloud API)
  → Clip Validation (Reliability layer)
  → High-Precision Cutting (FFmpeg Hybrid Mode)
  → Vertical Reframing (FFmpeg + MediaPipe)
  → Branding (Dynamic Subtitles + Overlays)
  → Final Publication-Ready Clips in /output
```

---

## 2. Technical Stack

| Component | Technology | Role |
|---|---|---|
| Audio | FFmpeg | Extraction & Normalization |
| ASR | faster-whisper | High-speed local transcription |
| AI Analysis | Ollama / MiniMax | Semantic content understanding |
| Validation | Pure Python | Timestamp & Logic verification |
| Video Ops | FFmpeg | Cutting & filtergraph processing |
| AI Vision | MediaPipe | Face detection for crop tracking |
| Interface | Gradio | Local web server (localhost:7860) |

---

## 3. Hardware Profiles

| Profile | GPU | Whisper Config | LLM Config | FFmpeg Workers |
|---|---|---|---|---|
| Development | RTX 3060 12GB | medium (int8) | mistral:7b | 2 |
| Production | RTX 5070 16GB+ | large-v2 (fp16) | llama3:70b | 4-6 |

---

## 4. Key Components

### 4.1 Phase 4: Validation (The Reliability Engine)
The system applies several filters to candidate clips:
1. **Bounds Check:** Ensure timestamps are within video duration.
2. **Duration Filter:** Enforce min/max clip lengths.
3. **Transcript Snapping:** Align clip start/end to actual sentence boundaries from the ASR.
4. **Margin Expansion:** Add natural padding (e.g., 2s) to prevent jarring cuts.
5. **Overlap Resolution:** Resolve conflicting segments by prioritizing higher AI "scores".

### 4.2 Phase 5: High-Precision Cutting
Uses a **Hybrid Seek Mode** to ensure frame-perfect cuts without the overhead of full re-encoding when possible, while avoiding the inaccuracy of `-c copy` on non-keyframes.

### 4.3 Phase 6: Vertical Reframing (9:16)
Three strategies:
- `center`: Fixed center crop (fallback).
- `smart`: Focus on areas with high motion (ideal for gaming).
- `face`: Face-tracking crop using MediaPipe (ideal for podcasts).

---

## 5. Environment Configuration (`.env`)

- `OLLAMA_MODEL`: Target LLM.
- `WHISPER_MODEL`: Accuracy level vs speed.
- `MAX_WORKERS`: Parallelism level for CPU/GPU.
- `STREAMER_NAME` & `CHANNEL_HANDLE`: Branding assets.

---

## 6. Future Roadmap

- **Audio Peak Detection:** Correlate ASR with audio energy levels for better "energy" detection.
- **Reranking:** Use semantic embeddings to better rank viral potential.
- **Advanced Branding:** "Karaoke style" word-level subtitle animations.
- **Automation:** Watch-folder monitoring and auto-upload to social platforms.

---

*Version 1.0 — April 2026*
