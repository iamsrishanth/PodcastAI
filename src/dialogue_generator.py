"""
Dialogue Generation Module for PodcastAI.
Uses Google Gemini API to generate natural conversations from scenario prompts.
"""

import json
import re
from dataclasses import dataclass
from typing import Optional
import google.generativeai as genai

from .config import get_config


@dataclass
class DialogueLine:
    """Represents a single line of dialogue."""
    speaker: str          # "A" or "B"
    name: str             # Character name (e.g., "Alex")
    text: str             # The actual dialogue text
    start: float          # Start time in seconds
    duration: float       # Estimated duration in seconds
    emotion: str = "neutral"  # Emotional tone


@dataclass
class ConversationScript:
    """Complete conversation script with metadata."""
    lines: list[DialogueLine]
    speaker_a_name: str
    speaker_b_name: str
    total_duration: float
    scene_description: str = ""
    
    def get_speaker_lines(self, speaker: str) -> list[DialogueLine]:
        """Get all lines for a specific speaker."""
        return [line for line in self.lines if line.speaker == speaker]
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "speaker_a_name": self.speaker_a_name,
            "speaker_b_name": self.speaker_b_name,
            "total_duration": self.total_duration,
            "scene_description": self.scene_description,
            "lines": [
                {
                    "speaker": line.speaker,
                    "name": line.name,
                    "text": line.text,
                    "start": line.start,
                    "duration": line.duration,
                    "emotion": line.emotion
                }
                for line in self.lines
            ]
        }


DIALOGUE_PROMPT_TEMPLATE = """
You are a scriptwriter creating a natural conversation between two people.

SCENARIO: {scenario}

CHARACTERS:
- Speaker A: {speaker_a_name}
- Speaker B: {speaker_b_name}

REQUIREMENTS:
- Create a natural, engaging conversation
- Target duration: {target_duration} seconds (approximately {num_exchanges} exchanges)
- Include varied emotions and reactions
- Keep each line concise (under 30 words)
- Make it feel like a real podcast/interview

OUTPUT FORMAT (strict JSON):
{{
    "scene_description": "Brief description of the setting",
    "lines": [
        {{"speaker": "A", "text": "dialogue text", "emotion": "friendly"}},
        {{"speaker": "B", "text": "response text", "emotion": "curious"}}
    ]
}}

VALID EMOTIONS: friendly, curious, excited, thoughtful, amused, serious, surprised, warm, neutral

Generate the conversation now:
"""


def configure_genai(api_key: Optional[str] = None) -> None:
    """Configure the Gemini API with the provided or default API key."""
    config = get_config()
    key = api_key or config.gemini_api_key
    if not key:
        raise ValueError("Gemini API key not provided. Set GEMINI_API_KEY in environment.")
    genai.configure(api_key=key)


def parse_dialogue_response(response_text: str, speaker_a_name: str, speaker_b_name: str) -> ConversationScript:
    """Parse the LLM response into a ConversationScript object."""
    # Try to extract JSON from the response
    json_match = re.search(r'\{[\s\S]*\}', response_text)
    if not json_match:
        raise ValueError("Could not find JSON in response")
    
    try:
        data = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}")
    
    lines = []
    current_time = 0.0
    
    for item in data.get("lines", []):
        speaker = item.get("speaker", "A")
        text = item.get("text", "")
        emotion = item.get("emotion", "neutral")
        
        # Estimate duration based on word count (~150 words per minute)
        word_count = len(text.split())
        duration = max(1.0, word_count / 2.5)  # ~2.5 words per second
        
        name = speaker_a_name if speaker == "A" else speaker_b_name
        
        lines.append(DialogueLine(
            speaker=speaker,
            name=name,
            text=text,
            start=current_time,
            duration=duration,
            emotion=emotion
        ))
        
        # Add small pause between lines
        current_time += duration + 0.3
    
    total_duration = current_time if lines else 0.0
    
    return ConversationScript(
        lines=lines,
        speaker_a_name=speaker_a_name,
        speaker_b_name=speaker_b_name,
        total_duration=total_duration,
        scene_description=data.get("scene_description", "")
    )


def generate_dialogue(
    scenario: str,
    speaker_a_name: str = "Alex",
    speaker_b_name: str = "Sam",
    target_duration: int = 45,
    api_key: Optional[str] = None
) -> ConversationScript:
    """
    Generate a conversation script from a scenario prompt.
    
    Args:
        scenario: Description of what the conversation should be about
        speaker_a_name: Name for the first speaker
        speaker_b_name: Name for the second speaker
        target_duration: Target duration in seconds
        api_key: Optional Gemini API key (uses config if not provided)
    
    Returns:
        ConversationScript object with the generated dialogue
    """
    configure_genai(api_key)
    config = get_config()
    
    # Calculate approximate number of exchanges
    num_exchanges = max(4, target_duration // 8)  # ~8 seconds per exchange
    
    prompt = DIALOGUE_PROMPT_TEMPLATE.format(
        scenario=scenario,
        speaker_a_name=speaker_a_name,
        speaker_b_name=speaker_b_name,
        target_duration=target_duration,
        num_exchanges=num_exchanges
    )
    
    model = genai.GenerativeModel(config.dialogue.model)
    
    response = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=config.dialogue.temperature,
            max_output_tokens=2048
        )
    )
    
    return parse_dialogue_response(
        response.text,
        speaker_a_name,
        speaker_b_name
    )


def save_script(script: ConversationScript, output_path: str) -> None:
    """Save a conversation script to a JSON file."""
    from pathlib import Path
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(script.to_dict(), f, indent=2, ensure_ascii=False)


def load_script(input_path: str) -> ConversationScript:
    """Load a conversation script from a JSON file."""
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    lines = [
        DialogueLine(
            speaker=line["speaker"],
            name=line["name"],
            text=line["text"],
            start=line["start"],
            duration=line["duration"],
            emotion=line.get("emotion", "neutral")
        )
        for line in data["lines"]
    ]
    
    return ConversationScript(
        lines=lines,
        speaker_a_name=data["speaker_a_name"],
        speaker_b_name=data["speaker_b_name"],
        total_duration=data["total_duration"],
        scene_description=data.get("scene_description", "")
    )
