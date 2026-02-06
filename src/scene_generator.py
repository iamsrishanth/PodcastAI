"""
Scene Generation Module for PodcastAI.
Uses Replicate API for cloud-based Stable Diffusion XL image generation.
"""

import os
from pathlib import Path
from typing import Optional, Literal
import urllib.request
import time

try:
    import replicate
    HAS_REPLICATE = True
except ImportError:
    HAS_REPLICATE = False

from .config import get_config


# Preset scene prompts for common scenarios
SCENE_PRESETS = {
    "office": {
        "prompt": "Modern corporate office meeting room, two empty chairs facing each other, professional lighting, wooden conference table, glass walls, city view background, photorealistic, high quality, 16:9 aspect ratio",
        "negative_prompt": "people, faces, blur, distortion, text, watermark"
    },
    "cafe": {
        "prompt": "Cozy coffee shop interior, warm lighting, two comfortable armchairs, small round table between them, bookshelves in background, plants, modern cafe aesthetic, photorealistic, 16:9 aspect ratio",
        "negative_prompt": "people, faces, blur, distortion, text, watermark"
    },
    "park": {
        "prompt": "Beautiful city park on sunny day, park bench for two people, green trees, walking path, blue sky with clouds, natural lighting, photorealistic, 16:9 aspect ratio",
        "negative_prompt": "people, faces, blur, distortion, text, watermark"
    },
    "studio": {
        "prompt": "Professional podcast studio, modern studio setup, two microphones on stands, acoustic panels on walls, soft professional lighting, minimalist design, photorealistic, 16:9 aspect ratio",
        "negative_prompt": "people, faces, blur, distortion, text, watermark"
    },
    "living_room": {
        "prompt": "Modern living room interior, comfortable sofa, ambient lighting, large windows, plants, minimalist furniture, warm atmosphere, photorealistic, 16:9 aspect ratio",
        "negative_prompt": "people, faces, blur, distortion, text, watermark"
    }
}


def configure_replicate(api_token: Optional[str] = None) -> None:
    """Configure Replicate API with the provided or default token."""
    config = get_config()
    token = api_token or config.replicate_api_key
    
    if not token:
        raise ValueError(
            "Replicate API token not provided. "
            "Set REPLICATE_API_TOKEN in environment or pass api_token parameter."
        )
    
    os.environ["REPLICATE_API_TOKEN"] = token


def generate_scene(
    prompt: str,
    output_path: Path,
    negative_prompt: str = "people, faces, blur, distortion, text, watermark",
    width: int = 1280,
    height: int = 720,
    api_token: Optional[str] = None
) -> Path:
    """
    Generate a background scene using Stable Diffusion XL via Replicate.
    
    Args:
        prompt: Text description of the scene to generate
        output_path: Path to save the generated image
        negative_prompt: Things to avoid in the generation
        width: Image width (default 1280 for 720p)
        height: Image height (default 720 for 720p)
        api_token: Optional Replicate API token
    
    Returns:
        Path to the generated image
    """
    if not HAS_REPLICATE:
        raise ImportError("replicate is required. Install with: pip install replicate")
    
    configure_replicate(api_token)
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Use SDXL model on Replicate
    output = replicate.run(
        "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
        input={
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "num_outputs": 1,
            "guidance_scale": 7.5,
            "num_inference_steps": 30
        }
    )
    
    # Download the generated image
    if output and len(output) > 0:
        image_url = output[0]
        urllib.request.urlretrieve(image_url, str(output_path))
        return output_path
    else:
        raise RuntimeError("Failed to generate scene: No output from Replicate")


def get_preset_scene(
    scene_type: Literal["office", "cafe", "park", "studio", "living_room"],
    output_path: Path,
    api_token: Optional[str] = None
) -> Path:
    """
    Generate a scene using a preset configuration.
    
    Args:
        scene_type: Type of scene to generate
        output_path: Path to save the generated image
        api_token: Optional Replicate API token
    
    Returns:
        Path to the generated image
    """
    if scene_type not in SCENE_PRESETS:
        raise ValueError(f"Unknown scene type: {scene_type}. Available: {list(SCENE_PRESETS.keys())}")
    
    preset = SCENE_PRESETS[scene_type]
    
    return generate_scene(
        prompt=preset["prompt"],
        output_path=output_path,
        negative_prompt=preset["negative_prompt"],
        api_token=api_token
    )


def generate_scene_from_scenario(
    scenario: str,
    output_path: Path,
    api_token: Optional[str] = None
) -> Path:
    """
    Generate a background scene based on a conversation scenario.
    
    This automatically creates a suitable prompt based on the scenario description.
    
    Args:
        scenario: Description of the conversation scenario
        output_path: Path to save the generated image
        api_token: Optional Replicate API token
    
    Returns:
        Path to the generated image
    """
    # Simple keyword matching to select appropriate scene
    scenario_lower = scenario.lower()
    
    if any(word in scenario_lower for word in ["office", "work", "business", "meeting", "corporate"]):
        return get_preset_scene("office", output_path, api_token)
    elif any(word in scenario_lower for word in ["coffee", "cafe", "tea", "lunch", "breakfast"]):
        return get_preset_scene("cafe", output_path, api_token)
    elif any(word in scenario_lower for word in ["park", "outdoor", "nature", "walk", "outside"]):
        return get_preset_scene("park", output_path, api_token)
    elif any(word in scenario_lower for word in ["podcast", "interview", "studio", "recording"]):
        return get_preset_scene("studio", output_path, api_token)
    elif any(word in scenario_lower for word in ["home", "living", "casual", "friend"]):
        return get_preset_scene("living_room", output_path, api_token)
    else:
        # Default to studio for podcasts
        return get_preset_scene("studio", output_path, api_token)


def use_local_background(
    image_path: Path,
    output_path: Path = None,
    resize_to: tuple[int, int] = (1280, 720)
) -> Path:
    """
    Use a local image as background instead of generating one.
    
    Args:
        image_path: Path to the local background image
        output_path: Optional path to save the resized image
        resize_to: Target size (width, height)
    
    Returns:
        Path to the background image
    """
    from PIL import Image
    
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Background image not found: {image_path}")
    
    img = Image.open(image_path)
    
    # Resize if needed
    if resize_to and img.size != resize_to:
        img = img.resize(resize_to, Image.Resampling.LANCZOS)
    
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)
        return output_path
    
    return image_path
