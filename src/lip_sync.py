"""
Lip Sync Animation Module for PodcastAI.
Uses Wav2Lip to animate portrait images with speech audio.
Optimized for 4GB VRAM GPUs.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, Tuple
import shutil

from .config import get_config


# Wav2Lip model configuration
WAV2LIP_REPO = "https://github.com/Rudrabha/Wav2Lip.git"
WAV2LIP_CHECKPOINT_URL = "https://huggingface.co/Camenduru/Wav2Lip/resolve/main/checkpoints/wav2lip_gan.pth"
FACE_DETECTION_MODEL_URL = "https://huggingface.co/Camenduru/Wav2Lip/resolve/main/checkpoints/s3fd.pth"


def check_wav2lip_installation(models_dir: Path) -> dict:
    """
    Check if Wav2Lip is properly installed and models are available.
    
    Returns:
        Dictionary with installation status
    """
    wav2lip_dir = models_dir / "Wav2Lip"
    checkpoint_path = models_dir / "wav2lip_gan.pth"
    face_det_path = models_dir / "s3fd.pth"
    
    return {
        "wav2lip_installed": wav2lip_dir.exists() and (wav2lip_dir / "inference.py").exists(),
        "checkpoint_exists": checkpoint_path.exists(),
        "face_detection_exists": face_det_path.exists(),
        "wav2lip_dir": wav2lip_dir,
        "checkpoint_path": checkpoint_path,
        "face_detection_path": face_det_path
    }


def setup_wav2lip(models_dir: Path = None, force: bool = False) -> Path:
    """
    Download and set up Wav2Lip repository and models.
    
    Args:
        models_dir: Directory to install Wav2Lip
        force: Force reinstallation even if already installed
    
    Returns:
        Path to the Wav2Lip directory
    """
    config = get_config()
    models_dir = Path(models_dir or config.models_dir)
    models_dir.mkdir(parents=True, exist_ok=True)
    
    status = check_wav2lip_installation(models_dir)
    
    # Clone Wav2Lip repository
    wav2lip_dir = status["wav2lip_dir"]
    if force or not status["wav2lip_installed"]:
        print("Cloning Wav2Lip repository...")
        if wav2lip_dir.exists():
            shutil.rmtree(wav2lip_dir)
        
        subprocess.run(
            ["git", "clone", WAV2LIP_REPO, str(wav2lip_dir)],
            check=True
        )
    
    # Download Wav2Lip checkpoint
    checkpoint_path = status["checkpoint_path"]
    if force or not status["checkpoint_exists"]:
        print("Downloading Wav2Lip checkpoint (~400MB)...")
        import urllib.request
        urllib.request.urlretrieve(WAV2LIP_CHECKPOINT_URL, str(checkpoint_path))
    
    # Download face detection model
    face_det_path = status["face_detection_path"]
    if force or not status["face_detection_exists"]:
        print("Downloading face detection model...")
        import urllib.request
        # Create face_detection/detection/sfd directory
        sfd_dir = wav2lip_dir / "face_detection" / "detection" / "sfd"
        sfd_dir.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(FACE_DETECTION_MODEL_URL, str(sfd_dir / "s3fd.pth"))
        # Also copy to models dir for reference
        shutil.copy(sfd_dir / "s3fd.pth", face_det_path)
    
    print("Wav2Lip setup complete!")
    return wav2lip_dir


def animate_portrait(
    portrait_path: Path,
    audio_path: Path,
    output_path: Path,
    models_dir: Path = None,
    batch_size: int = 16,
    face_det_batch_size: int = 8,
    resize_factor: int = 1
) -> Path:
    """
    Animate a portrait image with audio using Wav2Lip.
    
    Args:
        portrait_path: Path to the portrait image
        audio_path: Path to the audio file
        output_path: Path to save the output video
        models_dir: Directory containing Wav2Lip installation
        batch_size: Processing batch size (lower for less VRAM)
        face_det_batch_size: Face detection batch size (lower for less VRAM)
        resize_factor: Resize factor for processing (higher = lower resolution)
    
    Returns:
        Path to the generated video
    """
    config = get_config()
    models_dir = Path(models_dir or config.models_dir)
    
    status = check_wav2lip_installation(models_dir)
    
    if not status["wav2lip_installed"]:
        raise RuntimeError(
            "Wav2Lip not installed. Run setup_wav2lip() first or check installation."
        )
    
    if not status["checkpoint_exists"]:
        raise RuntimeError(
            f"Wav2Lip checkpoint not found at {status['checkpoint_path']}. "
            "Run setup_wav2lip() to download."
        )
    
    portrait_path = Path(portrait_path)
    audio_path = Path(audio_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    wav2lip_dir = status["wav2lip_dir"]
    checkpoint_path = status["checkpoint_path"]
    
    # Build Wav2Lip command
    # Lower batch sizes for 4GB VRAM compatibility
    cmd = [
        sys.executable,
        str(wav2lip_dir / "inference.py"),
        "--checkpoint_path", str(checkpoint_path),
        "--face", str(portrait_path),
        "--audio", str(audio_path),
        "--outfile", str(output_path),
        "--wav2lip_batch_size", str(batch_size),
        "--face_det_batch_size", str(face_det_batch_size),
        "--resize_factor", str(resize_factor),
        "--nosmooth"  # Faster processing
    ]
    
    # Run Wav2Lip
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = "0"  # Use first GPU
    
    result = subprocess.run(
        cmd,
        cwd=str(wav2lip_dir),
        env=env,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        raise RuntimeError(
            f"Wav2Lip failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
    
    if not output_path.exists():
        raise RuntimeError(f"Wav2Lip did not create output file: {output_path}")
    
    return output_path


def batch_animate(
    portrait_audio_pairs: list[Tuple[Path, Path]],
    output_dir: Path,
    models_dir: Path = None
) -> list[Path]:
    """
    Animate multiple portrait-audio pairs.
    
    Args:
        portrait_audio_pairs: List of (portrait_path, audio_path) tuples
        output_dir: Directory to save output videos
        models_dir: Directory containing Wav2Lip installation
    
    Returns:
        List of paths to generated videos
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    outputs = []
    for i, (portrait, audio) in enumerate(portrait_audio_pairs):
        output_path = output_dir / f"animated_{i:03d}.mp4"
        result = animate_portrait(portrait, audio, output_path, models_dir)
        outputs.append(result)
    
    return outputs


def create_static_video(
    image_path: Path,
    audio_path: Path,
    output_path: Path,
    fps: int = 25
) -> Path:
    """
    Create a video from a static image and audio (fallback if Wav2Lip unavailable).
    
    Args:
        image_path: Path to the image
        audio_path: Path to the audio
        output_path: Path to save the video
        fps: Frames per second
    
    Returns:
        Path to the generated video
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Use FFmpeg to create video from static image + audio
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(image_path),
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-r", str(fps),
        str(output_path)
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    
    return output_path
