"""
Main Pipeline Orchestrator for PodcastAI.
Coordinates all modules to generate conversational videos.
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import logging

from .config import Config, get_config
from .dialogue_generator import generate_dialogue, ConversationScript, save_script
from .tts_engine import generate_conversation_audio, AudioFile
from .compositor import composite_scene, remove_background
from .scene_generator import generate_scene_from_scenario, use_local_background
from .lip_sync import animate_portrait, check_wav2lip_installation, create_static_video
from .video_assembler import assemble_conversation_video, finalize_video


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result of a pipeline execution."""
    success: bool
    output_path: Optional[Path]
    script: Optional[ConversationScript]
    error: Optional[str] = None
    intermediate_files: dict = None


class ConversationPipeline:
    """
    Main pipeline for generating conversational videos.
    
    This class orchestrates all the modules to create a complete video
    from portraits and a scenario description.
    """
    
    def __init__(self, config: Config = None):
        """Initialize the pipeline with configuration."""
        self.config = config or get_config()
        self.temp_dir = self.config.temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def validate_inputs(
        self,
        portrait_a: Path,
        portrait_b: Path,
        scenario: str
    ) -> list[str]:
        """Validate input files and parameters."""
        issues = []
        
        if not Path(portrait_a).exists():
            issues.append(f"Portrait A not found: {portrait_a}")
        
        if not Path(portrait_b).exists():
            issues.append(f"Portrait B not found: {portrait_b}")
        
        if not scenario or len(scenario.strip()) < 10:
            issues.append("Scenario description is too short (min 10 characters)")
        
        # Check API keys
        config_issues = self.config.validate()
        issues.extend(config_issues)
        
        return issues
    
    def generate(
        self,
        portrait_a: Path,
        portrait_b: Path,
        scenario: str,
        output_path: Path,
        speaker_a_name: str = "Alex",
        speaker_b_name: str = "Sam",
        background_path: Optional[Path] = None,
        use_lip_sync: bool = True,
        voice_a: Optional[str] = None,
        voice_b: Optional[str] = None
    ) -> PipelineResult:
        """
        Generate a conversational video.
        
        Args:
            portrait_a: Path to first portrait image
            portrait_b: Path to second portrait image
            scenario: Description of the conversation
            output_path: Path for the final output video
            speaker_a_name: Name for speaker A
            speaker_b_name: Name for speaker B
            background_path: Optional custom background image
            use_lip_sync: Whether to use Wav2Lip (False for static video)
            voice_a: Optional voice for speaker A
            voice_b: Optional voice for speaker B
        
        Returns:
            PipelineResult with status and output
        """
        portrait_a = Path(portrait_a)
        portrait_b = Path(portrait_b)
        output_path = Path(output_path)
        
        intermediate_files = {}
        
        try:
            # Step 1: Validate inputs
            logger.info("Step 1/7: Validating inputs...")
            issues = self.validate_inputs(portrait_a, portrait_b, scenario)
            if issues:
                return PipelineResult(
                    success=False,
                    output_path=None,
                    script=None,
                    error=f"Validation failed: {'; '.join(issues)}"
                )
            
            # Step 2: Generate dialogue
            logger.info("Step 2/7: Generating dialogue...")
            script = generate_dialogue(
                scenario=scenario,
                speaker_a_name=speaker_a_name,
                speaker_b_name=speaker_b_name,
                target_duration=self.config.dialogue.target_duration_seconds
            )
            
            # Save script for reference
            script_path = self.temp_dir / "script.json"
            save_script(script, str(script_path))
            intermediate_files["script"] = script_path
            
            logger.info(f"  Generated {len(script.lines)} dialogue lines")
            
            # Step 3: Generate TTS audio
            logger.info("Step 3/7: Generating speech audio...")
            audio_files = generate_conversation_audio(
                script=script,
                voice_a=voice_a or self.config.tts.voice_a,
                voice_b=voice_b or self.config.tts.voice_b,
                output_dir=self.temp_dir / "audio"
            )
            intermediate_files["audio_a"] = [af.path for af in audio_files["A"]]
            intermediate_files["audio_b"] = [af.path for af in audio_files["B"]]
            
            # Step 4: Generate or load background
            logger.info("Step 4/7: Preparing background scene...")
            if background_path and Path(background_path).exists():
                background = use_local_background(
                    background_path,
                    self.temp_dir / "background.png"
                )
            else:
                background = generate_scene_from_scenario(
                    scenario,
                    self.temp_dir / "background.png"
                )
            intermediate_files["background"] = background
            
            # Step 5: Animate portraits with lip sync
            logger.info("Step 5/7: Animating portraits...")
            
            # Check if Wav2Lip is available
            wav2lip_status = check_wav2lip_installation(self.config.models_dir)
            
            if use_lip_sync and wav2lip_status["wav2lip_installed"]:
                # Combine audio for each speaker
                from .tts_engine import concatenate_audio_files
                
                audio_a_combined = self.temp_dir / "audio_a_combined.mp3"
                audio_b_combined = self.temp_dir / "audio_b_combined.mp3"
                
                concatenate_audio_files(
                    [af.path for af in audio_files["A"]],
                    audio_a_combined
                )
                concatenate_audio_files(
                    [af.path for af in audio_files["B"]],
                    audio_b_combined
                )
                
                # Animate with Wav2Lip
                video_a = animate_portrait(
                    portrait_a,
                    audio_a_combined,
                    self.temp_dir / "video_a.mp4"
                )
                video_b = animate_portrait(
                    portrait_b,
                    audio_b_combined,
                    self.temp_dir / "video_b.mp4"
                )
            else:
                # Fallback to static video
                logger.warning("  Wav2Lip not available, using static portraits")
                
                # Get total duration for each speaker
                from .tts_engine import get_audio_duration
                
                audio_a_combined = self.temp_dir / "audio_a_combined.mp3"
                audio_b_combined = self.temp_dir / "audio_b_combined.mp3"
                
                from .tts_engine import concatenate_audio_files
                concatenate_audio_files(
                    [af.path for af in audio_files["A"]],
                    audio_a_combined
                )
                concatenate_audio_files(
                    [af.path for af in audio_files["B"]],
                    audio_b_combined
                )
                
                video_a = create_static_video(
                    portrait_a,
                    audio_a_combined,
                    self.temp_dir / "video_a.mp4"
                )
                video_b = create_static_video(
                    portrait_b,
                    audio_b_combined,
                    self.temp_dir / "video_b.mp4"
                )
            
            intermediate_files["video_a"] = video_a
            intermediate_files["video_b"] = video_b
            
            # Step 6: Assemble final video
            logger.info("Step 6/7: Assembling final video...")
            assembled_video = self.temp_dir / "assembled.mp4"
            assemble_conversation_video(
                video_a=video_a,
                video_b=video_b,
                script=script,
                audio_files_a=[af.path for af in audio_files["A"]],
                audio_files_b=[af.path for af in audio_files["B"]],
                background=background,
                output_path=assembled_video,
                layout=self.config.video.layout
            )
            
            # Step 7: Finalize video
            logger.info("Step 7/7: Finalizing video...")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            finalize_video(
                assembled_video,
                output_path,
                resolution=self.config.video.resolution,
                fps=self.config.video.fps
            )
            
            logger.info(f"✓ Video generated successfully: {output_path}")
            
            return PipelineResult(
                success=True,
                output_path=output_path,
                script=script,
                intermediate_files=intermediate_files
            )
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            return PipelineResult(
                success=False,
                output_path=None,
                script=None,
                error=str(e),
                intermediate_files=intermediate_files
            )


def generate_conversation(
    portrait_a: Path,
    portrait_b: Path,
    scenario: str,
    output_path: Path,
    **kwargs
) -> PipelineResult:
    """
    Convenience function to generate a conversation video.
    
    This is the main entry point for generating videos.
    """
    pipeline = ConversationPipeline()
    return pipeline.generate(
        portrait_a=portrait_a,
        portrait_b=portrait_b,
        scenario=scenario,
        output_path=output_path,
        **kwargs
    )
