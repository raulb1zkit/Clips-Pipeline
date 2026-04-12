# 🎬 Video Highlight Pipeline

Automated extraction of 9:16 vertical clips from gaming streams and podcasts using AI.

> **Stack:** FFmpeg · faster-whisper · Ollama (local) / MiniMax-M2.5 (cloud) · MediaPipe · Gradio

---

## 🛠️ Pipeline Workflow

```text
Input Video
  → Audio Extraction (FFmpeg)
  → ASR Transcription (faster-whisper)
  → Semantic Analysis (Ollama local / MiniMax-M2.5 cloud)
  → Clip Validation (Logic-based verification)
  → Clip Cutting (FFmpeg hybrid mode)
  → 9:16 Vertical Reframing (FFmpeg + MediaPipe face detection)
  → Branding (ASS Subtitles + Logo + Overlays)
  → Final Clips in /output
```

---

## 🖥️ System Requirements

| Software | Requirement |
|---|---|
| Python | 3.10+ |
| FFmpeg | 5.0+ |
| CUDA | 11.8+ (for GPU acceleration) |
| Ollama | Recommended for local LLM inference |

### Target Hardware

| Profile | GPU | VRAM |
|---|---|---|
| Development | RTX 3060 | 12 GB |
| Production | RTX 5070 / 4090 | 16 GB+ |

---

## 🚀 Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/raulb1zkit/Clips-Pipeline.git
   cd Clips-Pipeline
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your specific configuration
   ```

4. **Prepare local LLM (Optional):**
   ```bash
   ollama pull mistral:7b      # Recommended for RTX 3060
   # ollama pull llama3:70b   # Recommended for RTX 5070+
   ```

5. **Run the Application:**
   ```bash
   python app.py
   # Interface available at http://localhost:7860
   ```

---

## ⚙️ Configuration (`.env`)

The project uses environment variables for easy switching between development and production environments.

- `LLM_PROVIDER`: `local` (Ollama) or `minimax` (Cloud API).
- `WHISPER_MODEL`: `medium` (dev) or `large-v2` (prod).
- `MAX_WORKERS`: Number of parallel FFmpeg processes.
- `STREAMER_NAME` & `CHANNEL_HANDLE`: Used for branding overlays.

---

## 📂 Project Structure

- `app.py`: Entry point for the Gradio User Interface.
- `pipeline/`: Core logic for each stage (transcription, cutting, reframing, branding).
- `prompts/`: Editable LLM prompt templates for different content types (gaming, podcast).
- `assets/`: Place your `logo.png` and `lower_third.png` here for branding.
- `docs/`: Legacy documentation and high-level design specs.

---

## 🧪 Design Principles

- **Security over LLM dependency:** The system validates all LLM outputs before processing any frames to ensure time-boundaries are correct and relevant.
- **Cache-First:** Transcriptions are cached locally to prevent redundant processing if the pipeline is restarted.
- **Privacy:** By default, and when using Ollama, the entire pipeline (including AI analysis) runs 100% locally.

---

*Version 1.0 — April 2026*
