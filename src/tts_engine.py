"""
Text-to-Speech Module for PodcastAI.
Uses Edge TTS (Microsoft's free TTS engine) to generate voice audio.
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

import edge_tts

from .config import get_config
from .dialogue_generator import ConversationScript, DialogueLine


# Available voice options
VOICE_PRESETS = {
    # Male voices
    "male_professional": "en-US-GuyNeural",
    "male_casual": "en-US-ChristopherNeural",
    "male_british": "en-GB-RyanNeural",
    
    # Female voices
    "female_professional": "en-US-JennyNeural",
    "female_casual": "en-US-AriaNeural",
    "female_british": "en-GB-SoniaNeural",
}


@dataclass
class AudioFile:
    """Represents a generated audio file with metadata."""
    path: Path
    duration: float
    speaker: str
    text: str


async def generate_speech_async(
    text: str,
    voice: str,
    output_path: Path,
    rate: str = "+0%",
    volume: str = "+0%"
) -> Path:
    """
    Generate speech audio from text using Edge TTS.
    
    Args:
        text: Text to convert to speech
        voice: Voice identifier (e.g., "en-US-GuyNeural")
        output_path: Path to save the audio file
        rate: Speech rate adjustment (e.g., "+10%", "-5%")
        volume: Volume adjustment (e.g., "+20%", "-10%")
    
    Returns:
        Path to the generated audio file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    await communicate.save(str(output_path))
    
    return output_path


def generate_speech(
    text: str,
    voice: str,
    output_path: Path,
    rate: str = "+0%",
    volume: str = "+0%"
) -> Path:
    """Synchronous wrapper for generate_speech_async."""
    return asyncio.run(generate_speech_async(text, voice, output_path, rate, volume))


def get_audio_duration(audio_path: Path) -> float:
    """
    Get the duration of an audio file in seconds using FFmpeg.
    
    Args:
        audio_path: Path to the audio file
    
    Returns:
        Duration in seconds
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(audio_path)
            ],
            capture_output=True,
            text=True,
            check=True
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as e:
        raise RuntimeError(f"Failed to get audio duration: {e}")


async def generate_line_audio_async(
    line: DialogueLine,
    voice: str,
    output_dir: Path,
    index: int
) -> AudioFile:
    """Generate audio for a single dialogue line."""
    output_path = output_dir / f"line_{index:03d}_{line.speaker}.mp3"
    
    await generate_speech_async(
        text=line.text,
        voice=voice,
        output_path=output_path
    )
    
    # Get actual duration
    duration = get_audio_duration(output_path)
    
    return AudioFile(
        path=output_path,
        duration=duration,
        speaker=line.speaker,
        text=line.text
    )


async def generate_conversation_audio_async(
    script: ConversationScript,
    voice_a: Optional[str] = None,
    voice_b: Optional[str] = None,
    output_dir: Optional[Path] = None
) -> dict[str, list[AudioFile]]:
    """
    Generate audio for all lines in a conversation script.
    
    Args:
        script: ConversationScript with dialogue lines
        voice_a: Voice for speaker A (uses config default if not provided)
        voice_b: Voice for speaker B (uses config default if not provided)
        output_dir: Directory to save audio files
    
    Returns:
        Dictionary with 'A' and 'B' keys containing lists of AudioFile objects
    """
    config = get_config()
    
    voice_a = voice_a or config.tts.voice_a
    voice_b = voice_b or config.tts.voice_b
    output_dir = output_dir or config.temp_dir / "audio"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    audio_files = {"A": [], "B": []}
    
    # Generate audio for each line
    tasks = []
    for i, line in enumerate(script.lines):
        voice = voice_a if line.speaker == "A" else voice_b
        tasks.append(generate_line_audio_async(line, voice, output_dir, i))
    
    results = await asyncio.gather(*tasks)
    
    for audio_file in results:
        audio_files[audio_file.speaker].append(audio_file)
    
    return audio_files


def generate_conversation_audio(
    script: ConversationScript,
    voice_a: Optional[str] = None,
    voice_b: Optional[str] = None,
    output_dir: Optional[Path] = None
) -> dict[str, list[AudioFile]]:
    """Synchronous wrapper for generate_conversation_audio_async."""
    return asyncio.run(
        generate_conversation_audio_async(script, voice_a, voice_b, output_dir)
    )


def list_available_voices(language_filter: str = "en") -> list[dict]:
    """
    List all available Edge TTS voices.
    
    Args:
        language_filter: Filter voices by language code (e.g., "en", "es")
    
    Returns:
        List of voice dictionaries with name, gender, and locale
    """
    async def _list_voices():
        voices = await edge_tts.list_voices()
        return [
            {
                "name": v["ShortName"],
                "gender": v["Gender"],
                "locale": v["Locale"]
            }
            for v in voices
            if v["Locale"].startswith(language_filter)
        ]
    
    return asyncio.run(_list_voices())


def concatenate_audio_files(
    audio_files: list[Path],
    output_path: Path,
    gaps: list[float] = None
) -> Path:
    """
    Concatenate multiple audio files with optional gaps between them.
    
    Args:
        audio_files: List of audio file paths to concatenate
        output_path: Path for the output file
        gaps: Optional list of gap durations (in seconds) between files
    
    Returns:
        Path to the concatenated audio file
    """
    if not audio_files:
        raise ValueError("No audio files to concatenate")
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create a filter complex for concatenation
    if gaps and len(gaps) == len(audio_files) - 1:
        # Complex concatenation with gaps using silence
        inputs = []
        filter_parts = []
        
        for i, audio_file in enumerate(audio_files):
            inputs.extend(["-i", str(audio_file)])
            filter_parts.append(f"[{i}:a]")
            if i < len(gaps):
                # Add silence
                filter_parts.append(f"aevalsrc=0:d={gaps[i]}[s{i}];")
        
        # This is simplified; for production, use proper filter_complex
        filter_complex = "".join(f"[{i}:a]" for i in range(len(audio_files))) + f"concat=n={len(audio_files)}:v=0:a=1[out]"
        
        cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", filter_complex, "-map", "[out]", str(output_path)]
    else:
        # Simple concatenation without gaps
        # Create a file list for concat demuxer
        list_file = output_path.parent / "concat_list.txt"
        with open(list_file, "w") as f:
            for audio_file in audio_files:
                f.write(f"file '{audio_file.absolute()}'\n")
        
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(output_path)]
    
    subprocess.run(cmd, check=True, capture_output=True)
    
    return output_path
