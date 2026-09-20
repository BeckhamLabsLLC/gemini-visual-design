"""Image editing via Gemini multi-turn.

Preferred over regenerating from scratch — edits build on previous
results to preserve what works and change what doesn't.
"""

import logging

from .asset_manager import save_generated
from .config import DEFAULT_IMAGE_TIER, IMAGE_MODELS, resolve_image_tier
from .gemini_client import GeminiClient
from .image_utils import read_image
from .style_profile import apply_to_prompt, load_profile

logger = logging.getLogger(__name__)


async def edit_image(
    client: GeminiClient,
    image_path: str,
    instruction: str,
    cwd: str = ".",
    preserve_style: bool = True,
    model: str = DEFAULT_IMAGE_TIER,
) -> dict:
    """Edit an existing image with natural language instruction.

    The original file is kept intact — the edit is saved as a new file.

    Args:
        client: GeminiClient instance
        image_path: Path to the image to edit
        instruction: Natural language edit instruction
        cwd: Current working directory (for finding style profile)
        preserve_style: Whether to apply style profile context to the edit
        model: Image tier to edit with (draft/fast/pro)

    Returns:
        Dict with: path, original_path, instruction, enhanced_instruction, model
    """
    tier, _alias_warning = resolve_image_tier(model)
    if tier == "auto":
        tier = DEFAULT_IMAGE_TIER

    # Read the original image
    image_data, mime_type = read_image(image_path)

    # Enhance the instruction with style context
    enhanced_instruction = instruction
    if preserve_style:
        profile = load_profile(cwd)
        if profile:
            enhanced_instruction = apply_to_prompt(profile, instruction)

    # Prefix to encourage editing over regeneration
    full_instruction = (
        f"Edit this image with the following changes: {enhanced_instruction}. "
        "Keep the overall composition and elements intact — only apply the requested changes."
    )

    # Send to Gemini for editing
    results = await client.edit_image_gemini(
        image_data=image_data,
        mime_type=mime_type,
        instruction=full_instruction,
        tier=tier,
    )

    # Save the edited result
    result = results[0]
    model_used = result.get("model") or IMAGE_MODELS[tier]
    metadata = {
        "prompt": instruction,
        "enhanced_prompt": enhanced_instruction,
        "original_path": image_path,
        "model": model_used,
        "tier": tier,
        "operation": "edit",
        "preserve_style": preserve_style,
    }

    path = save_generated(
        data=result["data"],
        mime_type=result["mime_type"],
        metadata=metadata,
        prefix="edit",
    )

    return {
        "path": str(path),
        "original_path": image_path,
        "instruction": instruction,
        "enhanced_instruction": enhanced_instruction,
        "model": model_used,
        "tier": tier,
        "text": result.get("text"),
    }
