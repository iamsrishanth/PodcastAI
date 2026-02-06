"""
FastAPI Backend for PodcastAI Web Interface.
Provides REST API and WebSocket for real-time progress updates.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.config import get_config, Config
from src.pipeline import ConversationPipeline, PipelineResult
from src.dialogue_generator import ConversationScript


# Data models
class GenerationRequest(BaseModel):
    scenario: str
    speaker_a_name: str = "Alex"
    speaker_b_name: str = "Sam"
    voice_a: Optional[str] = None
    voice_b: Optional[str] = None


class GenerationStatus(BaseModel):
    id: str
    status: str  # pending, processing, completed, failed
    current_step: int
    total_steps: int
    step_name: str
    progress_percent: float
    created_at: str
    completed_at: Optional[str] = None
    output_path: Optional[str] = None
    error: Optional[str] = None


class VideoHistoryItem(BaseModel):
    id: str
    scenario: str
    speaker_a_name: str
    speaker_b_name: str
    created_at: str
    duration: float
    output_path: str
    thumbnail_path: Optional[str] = None


# In-memory storage (use database in production)
generation_jobs: dict[str, GenerationStatus] = {}
video_history: list[VideoHistoryItem] = []
active_websockets: dict[str, list[WebSocket]] = {}


# Generation steps with descriptions
GENERATION_STEPS = [
    {"step": 1, "name": "Validating Inputs", "description": "Checking portrait images and API keys"},
    {"step": 2, "name": "Generating Dialogue", "description": "Creating natural conversation with AI"},
    {"step": 3, "name": "Synthesizing Speech", "description": "Converting text to realistic voice audio"},
    {"step": 4, "name": "Creating Background", "description": "Generating scene with AI"},
    {"step": 5, "name": "Animating Portraits", "description": "Adding lip sync to portraits"},
    {"step": 6, "name": "Assembling Video", "description": "Combining all elements"},
    {"step": 7, "name": "Finalizing", "description": "Encoding final video"}
]


def load_history():
    """Load video history from file."""
    global video_history
    config = get_config()
    history_file = config.outputs_dir / "history.json"
    
    if history_file.exists():
        with open(history_file, "r") as f:
            data = json.load(f)
            video_history = [VideoHistoryItem(**item) for item in data]


def save_history():
    """Save video history to file."""
    config = get_config()
    history_file = config.outputs_dir / "history.json"
    config.outputs_dir.mkdir(parents=True, exist_ok=True)
    
    with open(history_file, "w") as f:
        json.dump([item.model_dump() for item in video_history], f, indent=2)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load history on startup."""
    load_history()
    yield


app = FastAPI(
    title="PodcastAI API",
    description="Generate conversational videos from portraits",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
config = get_config()
config.outputs_dir.mkdir(parents=True, exist_ok=True)
config.inputs_dir.mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(config.outputs_dir)), name="outputs")
app.mount("/inputs", StaticFiles(directory=str(config.inputs_dir)), name="inputs")


async def notify_progress(job_id: str, status: GenerationStatus):
    """Send progress update to all connected WebSocket clients."""
    if job_id in active_websockets:
        for ws in active_websockets[job_id]:
            try:
                await ws.send_json(status.model_dump())
            except:
                pass


async def run_generation(
    job_id: str,
    portrait_a_path: Path,
    portrait_b_path: Path,
    request: GenerationRequest
):
    """Run the video generation pipeline with progress updates."""
    global video_history
    
    try:
        status = generation_jobs[job_id]
        config = get_config()
        output_path = config.outputs_dir / f"{job_id}.mp4"
        
        # Step 1: Validate
        status.current_step = 1
        status.step_name = "Validating Inputs"
        status.progress_percent = 0
        await notify_progress(job_id, status)
        await asyncio.sleep(0.5)  # Brief pause for UI
        
        pipeline = ConversationPipeline()
        issues = pipeline.validate_inputs(portrait_a_path, portrait_b_path, request.scenario)
        if issues:
            raise ValueError(f"Validation failed: {'; '.join(issues)}")
        
        # Step 2: Generate Dialogue
        status.current_step = 2
        status.step_name = "Generating Dialogue"
        status.progress_percent = 14
        await notify_progress(job_id, status)
        
        from src.dialogue_generator import generate_dialogue, save_script
        script = generate_dialogue(
            scenario=request.scenario,
            speaker_a_name=request.speaker_a_name,
            speaker_b_name=request.speaker_b_name
        )
        
        script_path = config.temp_dir / job_id / "script.json"
        script_path.parent.mkdir(parents=True, exist_ok=True)
        save_script(script, str(script_path))
        
        # Step 3: TTS
        status.current_step = 3
        status.step_name = "Synthesizing Speech"
        status.progress_percent = 28
        await notify_progress(job_id, status)
        
        from src.tts_engine import generate_conversation_audio
        audio_dir = config.temp_dir / job_id / "audio"
        audio_files = generate_conversation_audio(
            script=script,
            voice_a=request.voice_a or config.tts.voice_a,
            voice_b=request.voice_b or config.tts.voice_b,
            output_dir=audio_dir
        )
        
        # Step 4: Background
        status.current_step = 4
        status.step_name = "Creating Background"
        status.progress_percent = 42
        await notify_progress(job_id, status)
        
        from src.scene_generator import generate_scene_from_scenario
        background_path = config.temp_dir / job_id / "background.png"
        try:
            background = generate_scene_from_scenario(request.scenario, background_path)
        except Exception as e:
            # Fallback to a simple gradient background
            from PIL import Image
            img = Image.new('RGB', (1280, 720), color=(30, 30, 40))
            img.save(background_path)
            background = background_path
        
        # Step 5: Lip Sync
        status.current_step = 5
        status.step_name = "Animating Portraits"
        status.progress_percent = 56
        await notify_progress(job_id, status)
        
        from src.lip_sync import check_wav2lip_installation, create_static_video
        from src.tts_engine import concatenate_audio_files
        
        temp_dir = config.temp_dir / job_id
        audio_a_combined = temp_dir / "audio_a_combined.mp3"
        audio_b_combined = temp_dir / "audio_b_combined.mp3"
        
        concatenate_audio_files([af.path for af in audio_files["A"]], audio_a_combined)
        concatenate_audio_files([af.path for af in audio_files["B"]], audio_b_combined)
        
        # Use static video for now (Wav2Lip requires more setup)
        video_a = create_static_video(portrait_a_path, audio_a_combined, temp_dir / "video_a.mp4")
        video_b = create_static_video(portrait_b_path, audio_b_combined, temp_dir / "video_b.mp4")
        
        # Step 6: Assemble
        status.current_step = 6
        status.step_name = "Assembling Video"
        status.progress_percent = 70
        await notify_progress(job_id, status)
        
        from src.video_assembler import assemble_conversation_video
        assembled = temp_dir / "assembled.mp4"
        assemble_conversation_video(
            video_a=video_a,
            video_b=video_b,
            script=script,
            audio_files_a=[af.path for af in audio_files["A"]],
            audio_files_b=[af.path for af in audio_files["B"]],
            background=background,
            output_path=assembled
        )
        
        # Step 7: Finalize
        status.current_step = 7
        status.step_name = "Finalizing"
        status.progress_percent = 85
        await notify_progress(job_id, status)
        
        from src.video_assembler import finalize_video
        finalize_video(assembled, output_path)
        
        # Generate thumbnail
        thumbnail_path = config.outputs_dir / f"{job_id}_thumb.jpg"
        import subprocess
        subprocess.run([
            "ffmpeg", "-y", "-i", str(output_path),
            "-ss", "00:00:02", "-vframes", "1",
            "-vf", "scale=320:-1",
            str(thumbnail_path)
        ], capture_output=True)
        
        # Complete
        status.status = "completed"
        status.current_step = 7
        status.step_name = "Complete"
        status.progress_percent = 100
        status.completed_at = datetime.now().isoformat()
        status.output_path = f"/outputs/{job_id}.mp4"
        await notify_progress(job_id, status)
        
        # Add to history
        history_item = VideoHistoryItem(
            id=job_id,
            scenario=request.scenario,
            speaker_a_name=request.speaker_a_name,
            speaker_b_name=request.speaker_b_name,
            created_at=status.created_at,
            duration=script.total_duration,
            output_path=f"/outputs/{job_id}.mp4",
            thumbnail_path=f"/outputs/{job_id}_thumb.jpg" if thumbnail_path.exists() else None
        )
        video_history.insert(0, history_item)
        save_history()
        
    except Exception as e:
        status.status = "failed"
        status.error = str(e)
        status.completed_at = datetime.now().isoformat()
        await notify_progress(job_id, status)


@app.get("/")
async def root():
    return {"message": "PodcastAI API", "version": "1.0.0"}


@app.get("/api/steps")
async def get_steps():
    """Get list of generation steps."""
    return GENERATION_STEPS


@app.post("/api/generate")
async def start_generation(
    portrait_a: UploadFile = File(...),
    portrait_b: UploadFile = File(...),
    scenario: str = Form(...),
    speaker_a_name: str = Form("Alex"),
    speaker_b_name: str = Form("Sam"),
    voice_a: Optional[str] = Form(None),
    voice_b: Optional[str] = Form(None)
):
    """Start a new video generation job."""
    job_id = str(uuid.uuid4())[:8]
    config = get_config()
    
    # Save uploaded portraits
    portrait_a_path = config.inputs_dir / f"{job_id}_a{Path(portrait_a.filename).suffix}"
    portrait_b_path = config.inputs_dir / f"{job_id}_b{Path(portrait_b.filename).suffix}"
    
    with open(portrait_a_path, "wb") as f:
        f.write(await portrait_a.read())
    with open(portrait_b_path, "wb") as f:
        f.write(await portrait_b.read())
    
    # Create job status
    status = GenerationStatus(
        id=job_id,
        status="processing",
        current_step=0,
        total_steps=7,
        step_name="Starting",
        progress_percent=0,
        created_at=datetime.now().isoformat()
    )
    generation_jobs[job_id] = status
    
    # Start generation in background
    request = GenerationRequest(
        scenario=scenario,
        speaker_a_name=speaker_a_name,
        speaker_b_name=speaker_b_name,
        voice_a=voice_a,
        voice_b=voice_b
    )
    
    asyncio.create_task(run_generation(job_id, portrait_a_path, portrait_b_path, request))
    
    return {"job_id": job_id, "status": status.model_dump()}


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    """Get the status of a generation job."""
    if job_id not in generation_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return generation_jobs[job_id]


@app.websocket("/ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket for real-time progress updates."""
    await websocket.accept()
    
    if job_id not in active_websockets:
        active_websockets[job_id] = []
    active_websockets[job_id].append(websocket)
    
    try:
        # Send current status
        if job_id in generation_jobs:
            await websocket.send_json(generation_jobs[job_id].model_dump())
        
        # Keep connection alive
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        if job_id in active_websockets:
            active_websockets[job_id].remove(websocket)


@app.get("/api/history")
async def get_history():
    """Get video generation history."""
    return video_history


@app.delete("/api/history/{video_id}")
async def delete_from_history(video_id: str):
    """Delete a video from history."""
    global video_history
    video_history = [v for v in video_history if v.id != video_id]
    save_history()
    
    # Delete files
    config = get_config()
    video_path = config.outputs_dir / f"{video_id}.mp4"
    thumb_path = config.outputs_dir / f"{video_id}_thumb.jpg"
    
    if video_path.exists():
        video_path.unlink()
    if thumb_path.exists():
        thumb_path.unlink()
    
    return {"deleted": video_id}


@app.get("/api/voices")
async def get_voices():
    """Get available TTS voices."""
    from src.tts_engine import list_available_voices
    return list_available_voices("en")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
