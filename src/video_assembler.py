"""
Video Assembly Module for PodcastAI.
Uses FFmpeg to combine animated portraits, background, and audio into final video.
"""

import subprocess
from pathlib import Path
from typing import Optional, Literal
import json

from .config import get_config
from .dialogue_generator import ConversationScript


def get_video_info(video_path: Path) -> dict:
    """
    Get video metadata using FFprobe.
    
    Returns:
        Dictionary with duration, width, height, fps
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration",
        "-show_entries", "format=duration",
        "-of", "json",
        str(video_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    
    stream = data.get("streams", [{}])[0]
    format_info = data.get("format", {})
    
    # Parse frame rate (e.g., "25/1" -> 25.0)
    fps_str = stream.get("r_frame_rate", "25/1")
    if "/" in fps_str:
        num, den = fps_str.split("/")
        fps = float(num) / float(den)
    else:
        fps = float(fps_str)
    
    return {
        "width": int(stream.get("width", 1280)),
        "height": int(stream.get("height", 720)),
        "fps": fps,
        "duration": float(stream.get("duration") or format_info.get("duration", 0))
    }


def merge_videos_side_by_side(
    video_a: Path,
    video_b: Path,
    output_path: Path,
    target_width: int = 1280,
    target_height: int = 720
) -> Path:
    """
    Merge two videos side by side.
    
    Args:
        video_a: Left video path
        video_b: Right video path
        output_path: Output video path
        target_width: Final video width
        target_height: Final video height
    
    Returns:
        Path to the merged video
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    half_width = target_width // 2
    
    # Scale and position both videos side by side
    filter_complex = (
        f"[0:v]scale={half_width}:{target_height}:force_original_aspect_ratio=decrease,"
        f"pad={half_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[left];"
        f"[1:v]scale={half_width}:{target_height}:force_original_aspect_ratio=decrease,"
        f"pad={half_width}:{target_height}:(ow-iw)/2:(oh-ih)/2[right];"
        f"[left][right]hstack=inputs=2[v]"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_a),
        "-i", str(video_b),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        str(output_path)
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    
    return output_path


def overlay_on_background(
    video_a: Path,
    video_b: Path,
    background: Path,
    output_path: Path,
    layout: Literal["side-by-side", "conversation"] = "side-by-side"
) -> Path:
    """
    Overlay animated portraits on a background image.
    
    Args:
        video_a: Video of speaker A
        video_b: Video of speaker B
        background: Background image path
        output_path: Output video path
        layout: Layout style
    
    Returns:
        Path to the output video
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Get video durations to use the longer one
    info_a = get_video_info(video_a)
    info_b = get_video_info(video_b)
    max_duration = max(info_a["duration"], info_b["duration"])
    
    if layout == "side-by-side":
        # Position portraits on left and right of background
        filter_complex = (
            f"[0:v]loop=loop=-1:size=1:start=0,trim=duration={max_duration},"
            f"scale=1280:720,setsar=1[bg];"
            f"[1:v]scale=300:-1[a];"
            f"[2:v]scale=300:-1[b];"
            f"[bg][a]overlay=100:H-h-50[tmp];"
            f"[tmp][b]overlay=W-w-100:H-h-50[v]"
        )
    else:  # conversation layout
        filter_complex = (
            f"[0:v]loop=loop=-1:size=1:start=0,trim=duration={max_duration},"
            f"scale=1280:720,setsar=1[bg];"
            f"[1:v]scale=350:-1[a];"
            f"[2:v]scale=350:-1[b];"
            f"[bg][a]overlay=W/2-w-30:H-h-50[tmp];"
            f"[tmp][b]overlay=W/2+30:H-h-50[v]"
        )
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(background),
        "-i", str(video_a),
        "-i", str(video_b),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-t", str(max_duration),
        str(output_path)
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    
    return output_path


def add_audio_track(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    replace_audio: bool = True
) -> Path:
    """
    Add or replace audio track in a video.
    
    Args:
        video_path: Input video path
        audio_path: Audio file to add
        output_path: Output video path
        replace_audio: If True, replace existing audio; if False, mix
    
    Returns:
        Path to the output video
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if replace_audio:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-shortest",
            str(output_path)
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=longest[a]",
            "-c:v", "copy",
            "-map", "0:v:0",
            "-map", "[a]",
            str(output_path)
        ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    
    return output_path


def concatenate_audio_with_timing(
    audio_files: list[Path],
    timings: list[float],
    output_path: Path
) -> Path:
    """
    Concatenate audio files with specific timing gaps.
    
    Args:
        audio_files: List of audio file paths
        timings: Start time for each audio file
        output_path: Output audio file path
    
    Returns:
        Path to the concatenated audio
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if len(audio_files) == 0:
        raise ValueError("No audio files to concatenate")
    
    if len(audio_files) == 1:
        # Just copy the single file
        import shutil
        shutil.copy(audio_files[0], output_path)
        return output_path
    
    # Build complex filter for adelay
    inputs = []
    filter_parts = []
    
    for i, (audio_file, start_time) in enumerate(zip(audio_files, timings)):
        inputs.extend(["-i", str(audio_file)])
        delay_ms = int(start_time * 1000)
        filter_parts.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[a{i}]")
    
    # Mix all delayed audio streams
    mix_inputs = "".join(f"[a{i}]" for i in range(len(audio_files)))
    filter_parts.append(f"{mix_inputs}amix=inputs={len(audio_files)}:normalize=0[out]")
    
    filter_complex = ";".join(filter_parts)
    
    cmd = ["ffmpeg", "-y"] + inputs + [
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:a", "aac",
        str(output_path)
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    
    return output_path


def assemble_conversation_video(
    video_a: Path,
    video_b: Path,
    script: ConversationScript,
    audio_files_a: list[Path],
    audio_files_b: list[Path],
    background: Path,
    output_path: Path,
    layout: str = "side-by-side"
) -> Path:
    """
    Assemble the final conversation video.
    
    This is the main assembly function that combines all elements.
    
    Args:
        video_a: Animated video of speaker A
        video_b: Animated video of speaker B
        script: Conversation script with timing info
        audio_files_a: Audio files for speaker A
        audio_files_b: Audio files for speaker B
        background: Background image path
        output_path: Final output video path
        layout: Video layout style
    
    Returns:
        Path to the final video
    """
    config = get_config()
    temp_dir = config.temp_dir / "assembly"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Overlay portraits on background
    video_with_bg = temp_dir / "video_with_bg.mp4"
    overlay_on_background(video_a, video_b, background, video_with_bg, layout)
    
    # 2. Create combined audio track with proper timing
    all_audio = []
    all_timings = []
    
    for line in script.lines:
        if line.speaker == "A" and audio_files_a:
            all_audio.append(audio_files_a.pop(0))
        elif line.speaker == "B" and audio_files_b:
            all_audio.append(audio_files_b.pop(0))
        all_timings.append(line.start)
    
    combined_audio = temp_dir / "combined_audio.aac"
    concatenate_audio_with_timing(all_audio, all_timings, combined_audio)
    
    # 3. Add audio to video
    output_path = Path(output_path)
    add_audio_track(video_with_bg, combined_audio, output_path)
    
    return output_path


def finalize_video(
    video_path: Path,
    output_path: Path,
    resolution: str = "720p",
    fps: int = 25,
    codec: str = "libx264"
) -> Path:
    """
    Finalize video with specific output settings.
    
    Args:
        video_path: Input video path
        output_path: Output video path
        resolution: Target resolution ("720p", "1080p")
        fps: Target frame rate
        codec: Video codec
    
    Returns:
        Path to the finalized video
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    resolution_map = {
        "720p": (1280, 720),
        "1080p": (1920, 1080),
        "480p": (854, 480)
    }
    
    width, height = resolution_map.get(resolution, (1280, 720))
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2",
        "-c:v", codec,
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-r", str(fps),
        str(output_path)
    ]
    
    subprocess.run(cmd, check=True, capture_output=True)
    
    return output_path
