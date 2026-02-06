# Free MVP Architecture: Two-Portrait Conversational Video Generator

## Core Concept

Create conversational videos from two portrait images and a text scenario using **completely free and open-source tools**.

---

## 🎯 MVP Flow (Free Tools Version)

### Input Layer

- Two static portrait images (User A, User B)
- Text prompt describing the conversation scenario

### Processing Pipeline

| Stage | Free Tool | Function | Output |
|-------|-----------|----------|--------|
| 1 | **ComfyUI + Stable Diffusion** | Generate background scene | Background image |
| 2 | **PIL/OpenCV** | Composite portraits onto background | Static scene with both characters |
| 3 | **Google Gemini API (Free Tier)** | Generate realistic dialogue from scenario | Conversation script with timestamps |
| 4 | **Edge TTS / Coqui TTS** | Text-to-speech for each character | Audio files (User A & User B) |
| 5 | **SadTalker / Wav2Lip** | Animate portraits with lip sync | Individual talking head videos |
| 6 | **FFmpeg** | Combine videos, add audio, merge scenes | Final conversational video |

---

## 🛠️ Detailed Tool Breakdown

### 1. Scene Generation: **Stable Diffusion XL (SDXL)**

**Why:** Free, open-source, runs locally or via free APIs

- **Local:** [Automatic1111 WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) or [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- **Cloud Free Tier:** Replicate.com (limited free credits), Hugging Face Spaces
- **Alternative:** DALL-E 3 via Bing Image Creator (free with Microsoft account)

**Function:** Generate background scenes (office, coffee shop, park, etc.)

### 2. Image Compositing: **PIL (Pillow) + OpenCV**

**Why:** Free, simple Python libraries

```python
from PIL import Image
import cv2
```

**Function:**

- Remove backgrounds from portraits (using rembg library)
- Position portraits on generated background
- Adjust lighting and scale to match scene

### 3. Dialogue Generation: **Google Gemini API (Free Tier)**

**Why:** 1500 requests/day free tier, excellent at contextual dialogue

- **Alternative 1:** OpenAI GPT-3.5-Turbo (limited free credits)
- **Alternative 2:** Anthropic Claude (limited free tier)
- **Alternative 3:** Local LLMs via Ollama (Llama 3, Mistral)

**Function:** Convert scenario text into natural conversation with:

- Character assignments
- Dialogue timing
- Emotional tone markers

### 4. Text-to-Speech: **Edge TTS**

**Why:** Completely free, Microsoft's TTS engine, no API key needed

```bash
pip install edge-tts
```

**Alternatives:**

- **Coqui TTS** (open-source, 16+ languages)
- **Google TTS** (gTTS library - free)
- **pyttsx3** (offline TTS)

**Function:** Generate distinct voices for User A and User B

### 5. Lip Sync Animation: **SadTalker** (Recommended) or **Wav2Lip**

#### Option A: **SadTalker** ⭐ Recommended

**Why:** State-of-the-art, generates head movements AND lip sync

- GitHub: [SadTalker](https://github.com/OpenTalker/SadTalker)
- Free Colab notebooks available
- Produces more realistic results than Wav2Lip

#### Option B: **Wav2Lip**

**Why:** Fast, simpler, good lip sync accuracy

- GitHub: [Wav2Lip](https://github.com/Rudrabha/Wav2Lip)
- Lightweight, easier to set up locally

**Function:** Animate each portrait with corresponding audio

### 6. Video Assembly: **FFmpeg**

**Why:** Industry-standard, free, powerful

```bash
pip install ffmpeg-python
```

**Function:**

- Merge individual talking head videos
- Add audio tracks
- Apply transitions
- Export final MP4

---

## 💻 Implementation Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     INPUT HANDLER                           │
│  • Portrait A.jpg                                           │
│  • Portrait B.jpg                                           │
│  • Scenario text                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              SCENE GENERATION MODULE                        │
│  Tool: Stable Diffusion XL (local or Replicate API)        │
│  Output: background_scene.png                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              COMPOSITING MODULE                             │
│  Tool: PIL + OpenCV + rembg                                 │
│  • Remove portrait backgrounds                              │
│  • Position on scene                                        │
│  Output: composite_scene.png                                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              DIALOGUE GENERATION MODULE                     │
│  Tool: Google Gemini API (free tier)                        │
│  Output: conversation_script.json                           │
│  [                                                          │
│    {"speaker": "A", "text": "...", "start": 0.0},          │
│    {"speaker": "B", "text": "...", "start": 3.5}           │
│  ]                                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              TTS MODULE                                     │
│  Tool: Edge TTS                                             │
│  • Generate voice_A.mp3 (Male/Female voice 1)              │
│  • Generate voice_B.mp3 (Male/Female voice 2)              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              LIP SYNC & ANIMATION MODULE                    │
│  Tool: SadTalker                                            │
│  • Animate Portrait A with voice_A.mp3 → video_A.mp4       │
│  • Animate Portrait B with voice_B.mp4 → video_B.mp4       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              VIDEO ASSEMBLY MODULE                          │
│  Tool: FFmpeg                                               │
│  • Merge videos based on dialogue timing                    │
│  • Add background scene as static layer                     │
│  • Synchronize audio tracks                                │
│  Output: final_conversation.mp4                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📝 Example Free MVP Prompt Chain

### Step 1: Scene Generation (Stable Diffusion)

```
Prompt: "Modern office meeting room, two empty chairs facing each other, 
professional lighting, wooden conference table, corporate setting, 
photorealistic, wide shot, 16:9 aspect ratio"

Negative Prompt: "people, faces, blur, distortion"
```

### Step 2: Dialogue Generation (Gemini API)

```python
import google.generativeai as genai

prompt = """
Create a natural conversation between two colleagues (Alex and Sam) 
discussing a new AI product launch. The conversation should:
- Be 30-45 seconds long
- Include 4-6 exchanges
- Show professional tone with occasional humor
- Include natural pauses

Format as JSON with speaker, text, and estimated duration.
"""
```

### Step 3: TTS Generation (Edge TTS)

```bash
edge-tts --voice "en-US-GuyNeural" --text "Hello, Sam..." --write-media voice_A.mp3
edge-tts --voice "en-US-JennyNeural" --text "Hi Alex..." --write-media voice_B.mp3
```

### Step 4: Animation (SadTalker)

```bash
python inference.py --driven_audio voice_A.mp3 \
                    --source_image portrait_A.jpg \
                    --result_dir outputs/
```

---

## 🚀 Quick Start Setup

### Prerequisites

```bash
# Python 3.10+
python --version

# Install core dependencies
pip install pillow opencv-python rembg edge-tts ffmpeg-python
pip install google-generativeai  # For Gemini API
```

### Option 1: Local Setup (Recommended for control)

```bash
# 1. Install Stable Diffusion WebUI
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui
# Follow their installation guide

# 2. Install SadTalker
git clone https://github.com/OpenTalker/SadTalker
cd SadTalker
pip install -r requirements.txt
```

### Option 2: Cloud Setup (Easier, no GPU needed)

- Use **Google Colab** for SadTalker
- Use **Replicate API** for Stable Diffusion (free tier: 50 predictions/month)
- Use **Hugging Face Spaces** for quick testing

---

## 💰 Cost Comparison

| Component | Original (Paid) | Free Alternative | Monthly Cost |
|-----------|-----------------|------------------|--------------|
| Scene Gen | NanoBanana Pro | Stable Diffusion (local) | $0 |
| LLM | Veo3 (dialogue) | Gemini API (free tier) | $0 |
| TTS | Veo3 (native) | Edge TTS | $0 |
| Lip Sync | Veo3 (native) | SadTalker | $0 |
| Video | Veo3 | FFmpeg | $0 |
| **TOTAL** | **~$50-100+** | **$0** | **$0** |

---

## 🎬 Expected Output Quality

### Resolution

- **720p** (1280x720) - matches original spec
- Can be upgraded to 1080p with better hardware

### Frame Rate

- **24-30 FPS** (standard for video)

### Audio Quality

- **Edge TTS:** Near-human voice quality
- **16-bit 44.1kHz** audio output

### Lip Sync Accuracy

- **SadTalker:** ~85-90% accuracy with natural head movements
- **Wav2Lip:** ~80-85% accuracy, static head

---

## ⚠️ Limitations & Workarounds

| Limitation | Workaround |
|------------|------------|
| Processing time (5-10 min per video) | Pre-generate common scenes, cache results |
| GPU required for fast inference | Use Google Colab (free GPU) or cloud APIs |
| Lip sync not perfect for complex words | Use clearer audio, slower speech rate |
| Limited to English (some tools) | Check tool-specific language support |

---

## 🔄 Scalability Path

### Phase 1: MVP (Current)

- Local processing
- Manual prompt engineering
- Single video generation

### Phase 2: Automation

- Backend API (FastAPI)
- Queue system for batch processing
- Web interface for uploads

### Phase 3: Optimization

- Model quantization for faster inference
- Distributed processing
- CDN for output delivery

---

## 📚 Additional Resources

### Documentation Links

- [SadTalker GitHub](https://github.com/OpenTalker/SadTalker)
- [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
- [Edge TTS Documentation](https://github.com/rany2/edge-tts)
- [Gemini API Quickstart](https://ai.google.dev/tutorials/python_quickstart)
- [FFmpeg Python Tutorial](https://github.com/kkroening/ffmpeg-python)

### Community Support

- r/StableDiffusion (Reddit)
- Hugging Face Discord
- SadTalker Issues/Discussions

---

## 🎯 Next Steps

1. **Choose deployment strategy** (local vs cloud)
2. **Set up development environment**
3. **Test each component individually**
4. **Build integration pipeline**
5. **Create sample outputs**
6. **Optimize and refine**

---

**Ready to implement?** Let me know if you'd like me to create the actual Python implementation code for any of these components!
