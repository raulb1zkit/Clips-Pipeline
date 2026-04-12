# Hardware & Environment Setup

This document describes the technical environment required for the **Video Highlight Pipeline**.

---

## 🎯 Target Hardware

| Role | GPU | VRAM | Minimum RAM | Recommended OS |
|---|---|---|---|---|
| Development | NVIDIA RTX 3060 | 12 GB | 16 GB | Ubuntu 22.04+ / Windows 11 WSL2 |
| Production | NVIDIA RTX 5070+ | 16 GB+ | 32 GB | Ubuntu 22.04+ |

> **Note:** This pipeline is optimized for CUDA. It is not practical to run on CPU due to the high computational cost of `faster-whisper` and local LLM analysis.

---

## 📦 System Requirements

### Base Software

| Software | Minimum Version | Installation Command |
|---|---|---|
| Python | 3.10+ | `sudo apt install python3.10` |
| pip | 23+ | `python -m ensurepip` |
| FFmpeg | 5.0+ | `sudo apt install ffmpeg` |
| CUDA Toolkit | 11.8+ | See NVIDIA website |
| Git | Latest | `sudo apt install git` |

### NVIDIA CUDA Verification

```bash
# Check installed CUDA version
nvcc --version
nvidia-smi

# Verify GPU visibility in Python:
python3 -c "import torch; print(torch.cuda.is_available())"
```

---

## 🧠 Local LLM Setup (Ollama)

Ollama handles LLM inference locally.

```bash
# 1. Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Download models based on your hardware:
# --- Development (RTX 3060) ---
ollama pull mistral:7b     

# --- Production (RTX 5070+) ---
# ollama pull llama3:70b   
```

---

## ⚙️ Project Installation

```bash
# 1. Clone & Enter
git clone <YOUR_REPO_URL>
cd Clips-Pipeline

# 2. Virtual Environment
python3 -m venv venv
source venv/bin/activate

# 3. Dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configuration
cp .env.example .env
# Edit .env to match your hardware profile
```

---

## 🛠️ Validation Checklist

```bash
# 1. GPU available for Whisper
python3 -c "from faster_whisper import WhisperModel; m = WhisperModel('tiny', device='cuda'); print('Whisper OK')"

# 2. Ollama is running
curl http://localhost:11434/api/tags

# 3. FFmpeg is installed
ffmpeg -version

# 4. Launch the UI
python app.py
```

---

## 🧹 Performance & Maintenance

- **VRAM Management:** Sequentially executing Whisper and LLM ensures they both fit in 12GB VRAM.
- **Storage:** Allocate at least **20 GB** for the `cache/` directory (uncompressed audio can be large).
- **Subtitles:** The system uses ASS (Advanced Substation Alpha) format for precise timing and positioning of dynamic subtitles.

---

*Last updated: April 2026*
