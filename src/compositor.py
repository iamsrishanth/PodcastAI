"""
Image Compositing Module for PodcastAI.
Handles background removal, portrait positioning, and scene composition.
"""

from pathlib import Path
from typing import Tuple, Literal
from PIL import Image
import numpy as np

try:
    from rembg import remove as remove_bg
    HAS_REMBG = True
except ImportError:
    HAS_REMBG = False

from .config import get_config


def remove_background(image_path: Path, output_path: Path = None) -> Image.Image:
    """
    Remove background from a portrait image.
    
    Args:
        image_path: Path to the input image
        output_path: Optional path to save the result
    
    Returns:
        PIL Image with transparent background
    """
    if not HAS_REMBG:
        raise ImportError("rembg is required for background removal. Install with: pip install rembg")
    
    image_path = Path(image_path)
    with open(image_path, "rb") as f:
        input_data = f.read()
    
    output_data = remove_bg(input_data)
    
    # Convert to PIL Image
    from io import BytesIO
    result = Image.open(BytesIO(output_data)).convert("RGBA")
    
    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.save(output_path)
    
    return result


def resize_portrait(
    portrait: Image.Image,
    target_height: int,
    maintain_aspect: bool = True
) -> Image.Image:
    """
    Resize a portrait to a target height while maintaining aspect ratio.
    
    Args:
        portrait: PIL Image to resize
        target_height: Target height in pixels
        maintain_aspect: Whether to maintain aspect ratio
    
    Returns:
        Resized PIL Image
    """
    if maintain_aspect:
        aspect_ratio = portrait.width / portrait.height
        target_width = int(target_height * aspect_ratio)
    else:
        target_width = portrait.width
    
    return portrait.resize((target_width, target_height), Image.Resampling.LANCZOS)


def composite_portraits(
    background: Image.Image,
    portrait_a: Image.Image,
    portrait_b: Image.Image,
    layout: Literal["side-by-side", "conversation"] = "side-by-side",
    portrait_height_ratio: float = 0.7
) -> Image.Image:
    """
    Composite two portraits onto a background image.
    
    Args:
        background: Background image
        portrait_a: First portrait (left side)
        portrait_b: Second portrait (right side)
        layout: Layout style for positioning
        portrait_height_ratio: Portrait height as ratio of background height
    
    Returns:
        Composited image
    """
    # Ensure background is RGBA
    if background.mode != "RGBA":
        background = background.convert("RGBA")
    
    bg_width, bg_height = background.size
    target_portrait_height = int(bg_height * portrait_height_ratio)
    
    # Resize portraits
    portrait_a = resize_portrait(portrait_a, target_portrait_height)
    portrait_b = resize_portrait(portrait_b, target_portrait_height)
    
    # Create a copy of the background
    result = background.copy()
    
    if layout == "side-by-side":
        # Position portraits on left and right sides
        # Portrait A on left (facing right)
        pos_a_x = int(bg_width * 0.1)
        pos_a_y = bg_height - portrait_a.height - int(bg_height * 0.05)
        
        # Portrait B on right (facing left)
        pos_b_x = bg_width - portrait_b.width - int(bg_width * 0.1)
        pos_b_y = bg_height - portrait_b.height - int(bg_height * 0.05)
        
    elif layout == "conversation":
        # More intimate conversation layout (closer together)
        center_x = bg_width // 2
        
        pos_a_x = center_x - portrait_a.width - int(bg_width * 0.05)
        pos_a_y = bg_height - portrait_a.height - int(bg_height * 0.05)
        
        pos_b_x = center_x + int(bg_width * 0.05)
        pos_b_y = bg_height - portrait_b.height - int(bg_height * 0.05)
    
    # Paste portraits with alpha channel
    result.paste(portrait_a, (pos_a_x, pos_a_y), portrait_a)
    result.paste(portrait_b, (pos_b_x, pos_b_y), portrait_b)
    
    return result


def composite_scene(
    background_path: Path,
    portrait_a_path: Path,
    portrait_b_path: Path,
    output_path: Path,
    layout: Literal["side-by-side", "conversation"] = "side-by-side",
    remove_portrait_backgrounds: bool = True
) -> Path:
    """
    Create a complete composite scene from background and portrait images.
    
    Args:
        background_path: Path to background image
        portrait_a_path: Path to first portrait
        portrait_b_path: Path to second portrait
        output_path: Path to save the result
        layout: Layout style for positioning
        remove_portrait_backgrounds: Whether to remove portrait backgrounds
    
    Returns:
        Path to the saved composite image
    """
    # Load background
    background = Image.open(background_path).convert("RGBA")
    
    # Load and process portraits
    if remove_portrait_backgrounds:
        portrait_a = remove_background(portrait_a_path)
        portrait_b = remove_background(portrait_b_path)
    else:
        portrait_a = Image.open(portrait_a_path).convert("RGBA")
        portrait_b = Image.open(portrait_b_path).convert("RGBA")
    
    # Composite
    result = composite_portraits(background, portrait_a, portrait_b, layout)
    
    # Save
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to RGB for JPEG, keep RGBA for PNG
    if output_path.suffix.lower() in [".jpg", ".jpeg"]:
        result = result.convert("RGB")
    
    result.save(output_path)
    
    return output_path


def adjust_brightness(image: Image.Image, factor: float) -> Image.Image:
    """
    Adjust image brightness.
    
    Args:
        image: PIL Image to adjust
        factor: Brightness factor (1.0 = original, <1.0 = darker, >1.0 = brighter)
    
    Returns:
        Adjusted PIL Image
    """
    from PIL import ImageEnhance
    enhancer = ImageEnhance.Brightness(image)
    return enhancer.enhance(factor)


def adjust_contrast(image: Image.Image, factor: float) -> Image.Image:
    """
    Adjust image contrast.
    
    Args:
        image: PIL Image to adjust
        factor: Contrast factor (1.0 = original)
    
    Returns:
        Adjusted PIL Image
    """
    from PIL import ImageEnhance
    enhancer = ImageEnhance.Contrast(image)
    return enhancer.enhance(factor)


def create_video_frame(
    background: Image.Image,
    active_speaker: Literal["A", "B", None] = None,
    portrait_a_frame: Image.Image = None,
    portrait_b_frame: Image.Image = None,
    layout: str = "side-by-side"
) -> Image.Image:
    """
    Create a single video frame with optional speaker highlighting.
    
    This is used when generating the final video to show which speaker
    is currently active.
    
    Args:
        background: Background image
        active_speaker: Which speaker is currently talking ("A", "B", or None)
        portrait_a_frame: Current frame of portrait A (from Wav2Lip output)
        portrait_b_frame: Current frame of portrait B (from Wav2Lip output)
        layout: Layout style
    
    Returns:
        Composed frame as PIL Image
    """
    # This will be used in the video assembly phase
    # For now, just composite the frames onto the background
    result = background.copy()
    
    if portrait_a_frame and portrait_b_frame:
        result = composite_portraits(
            result,
            portrait_a_frame,
            portrait_b_frame,
            layout
        )
    
    return result
