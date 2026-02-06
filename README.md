# PodcastAI 🎙️

**Two-Portrait Conversational Video Generator**

Generate conversational videos from two portrait images and a text scenario using free and open-source tools.

## ✨ Features

- 🎭 **Lip Sync Animation** - Wav2Lip for realistic lip movements
- 🗣️ **Natural TTS** - Microsoft Edge TTS (100% free)
- 💬 **AI Dialogue** - Google Gemini generates natural conversations
- 🖼️ **Scene Generation** - Cloud-based Stable Diffusion XL
- 🎬 **FFmpeg Assembly** - Professional video composition
- 🌐 **Modern Web UI** - React frontend with real-time progress

---

## 🚀 Quick Start

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up API Keys

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your API keys:
# - GEMINI_API_KEY (free: https://aistudio.google.com/app/apikey)
# - REPLICATE_API_TOKEN (free tier: https://replicate.com)
```

### 3. Set Up Wav2Lip (First Time)

```bash
python main.py --setup
```

### 4. Start the Web App

**Option A: Web UI (Recommended)**

```bash
# Terminal 1: Start the backend API
python api.py

# Terminal 2: Start the frontend
cd frontend
npm install
npm run dev
```

Then open <http://localhost:5173>

**Option B: Command Line**

```bash
python main.py \
    --portrait-a inputs/alice.jpg \
    --portrait-b inputs/bob.jpg \
    --scenario "Two colleagues discussing AI" \
    --output outputs/conversation.mp4
```

---

## 🌐 Web Interface Features

| Feature | Description |
|---------|-------------|
| **Real-time Progress** | Watch each generation step with live updates |
| **Step Visualization** | See 7 detailed steps with descriptions |
| **Video History** | Browse and replay previously generated videos |
| **Drag & Drop** | Easy portrait upload with preview |
| **Voice Selection** | Choose from 10+ realistic voices |
| **Dark Theme** | Modern, eye-friendly design |

---

## 📋 CLI Options

| Option | Description |
|--------|-------------|
| `-a, --portrait-a` | First portrait image path |
| `-b, --portrait-b` | Second portrait image path |
| `-s, --scenario` | Conversation scenario description |
| `-o, --output` | Output video path |
| `--voice-a` | Voice for speaker A |
| `--voice-b` | Voice for speaker B |
| `--background` | Custom background image |
| `--no-lip-sync` | Use static portraits |
| `--setup` | Install Wav2Lip models |
| `--list-voices` | Show available voices |
| `--check` | Check installation status |

---

## 🏗️ Project Structure

```
PodcastAI/
├── src/                    # Python modules
│   ├── config.py           # Configuration
│   ├── dialogue_generator.py
│   ├── tts_engine.py
│   ├── compositor.py
│   ├── scene_generator.py
│   ├── lip_sync.py
│   ├── video_assembler.py
│   └── pipeline.py
├── frontend/               # React web app
│   ├── src/
│   │   ├── App.jsx         # Main component
│   │   ├── App.css
│   │   └── index.css       # Global styles
│   └── package.json
├── api.py                  # FastAPI backend
├── main.py                 # CLI entry point
└── requirements.txt
```

---

## 💻 System Requirements

- **Python**: 3.10+
- **Node.js**: 18+ (for frontend)
- **GPU**: CUDA GPU with 4GB+ VRAM (for Wav2Lip)
- **FFmpeg**: Required for video processing

---

## 🔑 API Keys Required

| Service | Purpose | Free Tier |
|---------|---------|-----------|
| Google Gemini | Dialogue generation | 1500 req/day |
| Replicate | Scene generation | 50 predictions/month |

---

## 📄 License

MIT License - Free to use and modify.
