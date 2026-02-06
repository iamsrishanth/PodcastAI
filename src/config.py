"""
Configuration management for PodcastAI.
Handles API keys, paths, and default settings.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class TTSConfig:
    """Text-to-Speech configuration."""
    voice_a: str = "en-US-GuyNeural"      # Male voice for speaker A
    voice_b: str = "en-US-JennyNeural"    # Female voice for speaker B
    rate: str = "+0%"                      # Speech rate adjustment
    volume: str = "+0%"                    # Volume adjustment


@dataclass
class DialogueConfig:
    """Dialogue generation configuration."""
    model: str = "gemini-1.5-flash"
    max_exchanges: int = 6
    target_duration_seconds: int = 45
    temperature: float = 0.7


@dataclass
class VideoConfig:
    """Video output configuration."""
    resolution: str = "720p"
    fps: int = 25
    codec: str = "libx264"
    audio_codec: str = "aac"
    layout: str = "side-by-side"  # or "picture-in-picture"


@dataclass
class LipSyncConfig:
    """Lip sync (Wav2Lip) configuration."""
    checkpoint_path: Optional[Path] = None
    use_gpu: bool = True
    batch_size: int = 16  # Lower for 4GB VRAM
    face_det_batch_size: int = 8  # Lower for 4GB VRAM
    resize_factor: int = 1


@dataclass
class Config:
    """Main configuration class for PodcastAI."""
    
    # API Keys (from environment variables)
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    replicate_api_key: str = field(default_factory=lambda: os.getenv("REPLICATE_API_TOKEN", ""))
    
    # Paths
    project_root: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    inputs_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "inputs")
    outputs_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "outputs")
    models_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "models")
    temp_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "temp")
    
    # Sub-configs
    tts: TTSConfig = field(default_factory=TTSConfig)
    dialogue: DialogueConfig = field(default_factory=DialogueConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    lip_sync: LipSyncConfig = field(default_factory=LipSyncConfig)
    
    def __post_init__(self):
        """Create necessary directories after initialization."""
        self.inputs_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> list[str]:
        """Validate configuration and return list of issues."""
        issues = []
        
        if not self.gemini_api_key:
            issues.append("GEMINI_API_KEY not set in environment")
        
        if not self.replicate_api_key:
            issues.append("REPLICATE_API_TOKEN not set (needed for scene generation)")
        
        return issues


# Global default configuration
_config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config) -> None:
    """Set the global configuration instance."""
    global _config
    _config = config
