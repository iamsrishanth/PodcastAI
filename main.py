#!/usr/bin/env python3
"""
PodcastAI - Two-Portrait Conversational Video Generator

Generate conversational videos from two portrait images and a text scenario.

Usage:
    python main.py --portrait-a portraits/alice.jpg \\
                   --portrait-b portraits/bob.jpg \\
                   --scenario "Two friends discussing weekend plans" \\
                   --output outputs/conversation.mp4
"""

import argparse
import sys
from pathlib import Path

from src.pipeline import ConversationPipeline, generate_conversation
from src.config import get_config, Config
from src.lip_sync import setup_wav2lip, check_wav2lip_installation
from src.tts_engine import list_available_voices


def main():
    parser = argparse.ArgumentParser(
        description="Generate conversational videos from portraits and text scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Basic usage
    python main.py -a portrait1.jpg -b portrait2.jpg -s "A job interview" -o output.mp4

    # With custom voices
    python main.py -a alice.jpg -b bob.jpg -s "Friends chatting" \\
                   --voice-a en-US-ChristopherNeural --voice-b en-US-AriaNeural

    # With custom background
    python main.py -a alice.jpg -b bob.jpg -s "Business meeting" \\
                   --background office.jpg -o output.mp4

    # Setup Wav2Lip (first time)
    python main.py --setup

    # List available voices
    python main.py --list-voices
        """
    )
    
    # Main arguments
    parser.add_argument(
        "-a", "--portrait-a",
        type=Path,
        help="Path to first portrait image"
    )
    parser.add_argument(
        "-b", "--portrait-b",
        type=Path,
        help="Path to second portrait image"
    )
    parser.add_argument(
        "-s", "--scenario",
        type=str,
        help="Conversation scenario description"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("outputs/conversation.mp4"),
        help="Output video path (default: outputs/conversation.mp4)"
    )
    
    # Optional arguments
    parser.add_argument(
        "--speaker-a-name",
        type=str,
        default="Alex",
        help="Name for speaker A (default: Alex)"
    )
    parser.add_argument(
        "--speaker-b-name",
        type=str,
        default="Sam",
        help="Name for speaker B (default: Sam)"
    )
    parser.add_argument(
        "--voice-a",
        type=str,
        help="Voice for speaker A (default: en-US-GuyNeural)"
    )
    parser.add_argument(
        "--voice-b",
        type=str,
        help="Voice for speaker B (default: en-US-JennyNeural)"
    )
    parser.add_argument(
        "--background",
        type=Path,
        help="Custom background image (auto-generated if not provided)"
    )
    parser.add_argument(
        "--no-lip-sync",
        action="store_true",
        help="Disable lip sync (use static portraits)"
    )
    parser.add_argument(
        "--resolution",
        choices=["480p", "720p", "1080p"],
        default="720p",
        help="Output resolution (default: 720p)"
    )
    
    # Setup commands
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Download and setup Wav2Lip models"
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="List available TTS voices"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check installation and dependencies"
    )
    
    args = parser.parse_args()
    
    # Handle setup commands
    if args.setup:
        print("Setting up Wav2Lip...")
        config = get_config()
        setup_wav2lip(config.models_dir)
        print("Setup complete!")
        return 0
    
    if args.list_voices:
        print("Available English TTS voices:")
        print("-" * 50)
        voices = list_available_voices("en")
        for voice in voices:
            print(f"  {voice['name']:30} ({voice['gender']})")
        return 0
    
    if args.check:
        print("Checking installation...")
        config = get_config()
        
        # Check Wav2Lip
        status = check_wav2lip_installation(config.models_dir)
        print(f"\nWav2Lip:")
        print(f"  Installed: {'✓' if status['wav2lip_installed'] else '✗'}")
        print(f"  Checkpoint: {'✓' if status['checkpoint_exists'] else '✗'}")
        print(f"  Face Detection: {'✓' if status['face_detection_exists'] else '✗'}")
        
        # Check config
        print(f"\nConfiguration:")
        issues = config.validate()
        if issues:
            for issue in issues:
                print(f"  ⚠ {issue}")
        else:
            print("  ✓ All API keys configured")
        
        # Check FFmpeg
        import subprocess
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            print(f"\nFFmpeg: ✓ Installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"\nFFmpeg: ✗ Not found - Please install FFmpeg")
        
        return 0
    
    # Validate required arguments for generation
    if not all([args.portrait_a, args.portrait_b, args.scenario]):
        parser.error("--portrait-a, --portrait-b, and --scenario are required for generation")
    
    # Run the pipeline
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║              PodcastAI - Conversation Generator               ║
╚══════════════════════════════════════════════════════════════╝

Portrait A: {args.portrait_a}
Portrait B: {args.portrait_b}
Scenario: {args.scenario[:50]}{'...' if len(args.scenario) > 50 else ''}
Output: {args.output}
    """)
    
    result = generate_conversation(
        portrait_a=args.portrait_a,
        portrait_b=args.portrait_b,
        scenario=args.scenario,
        output_path=args.output,
        speaker_a_name=args.speaker_a_name,
        speaker_b_name=args.speaker_b_name,
        background_path=args.background,
        use_lip_sync=not args.no_lip_sync,
        voice_a=args.voice_a,
        voice_b=args.voice_b
    )
    
    if result.success:
        print(f"\n✓ Video generated successfully!")
        print(f"  Output: {result.output_path}")
        print(f"  Duration: {result.script.total_duration:.1f}s")
        print(f"  Dialogue lines: {len(result.script.lines)}")
        return 0
    else:
        print(f"\n✗ Failed to generate video:")
        print(f"  {result.error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
