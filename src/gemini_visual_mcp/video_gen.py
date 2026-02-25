"""Video generation via Veo with async polling.

Supports Veo 2, Veo 3.1, and Veo 3.1 Fast models.
Generates short video clips with prompt enhancement.
"""

import logging
from typing import Optional

from .asset_manager import save_generated
from .gemini_client import GeminiClient
from .image_utils import read_image
from .prompt_engine import enhance
from .style_profile import load_profile

logger = logging.getLogger(__name__)


async def generate_video(
    client: GeminiClient,
    prompt: str,
    model: str = "veo-2",
    reference_image: Optional[str] = None,
    cwd: str = ".",
    use_profile: bool = True,
) -> dict:
    """Generate a video clip with the specified model.

    Args:
        client: GeminiClient instance
        prompt: Video description
        model: "veo-2", "veo-3.1", or "veo-3.1-fast"
        reference_image: Optional path to a reference image
        cwd: Current working directory for style profile
        use_profile: Whether to apply style profile to prompt

    Returns:
        Dict with: path, enhanced_prompt, model, warnings
    """
    # Load profile and enhance prompt
    profile = load_profile(cwd) if use_profile else None
    enhanced_prompt, warnings = enhance(prompt, profile=profile)

    # Read reference image if provided
    image_data = None
    image_mime = None
    if reference_image:
        image_data, image_mime = read_image(reference_image)

    # Start async generation
    operation = await client.generate_video(
        prompt=enhanced_prompt,
        model=model,
        image_data=image_data,
        image_mime_type=image_mime,
    )

    # Poll until complete
    results = await client.poll_video_operation(operation)

    # Save the first video result
    if not results:
        raise RuntimeError("Video generation completed but returned no results")

    result = results[0]
    metadata = {
        "prompt": prompt,
        "enhanced_prompt": enhanced_prompt,
        "model": model,
        "operation": "video_generation",
        "reference_image": reference_image,
        "warnings": [w.to_dict() for w in warnings],
    }

    path = save_generated(
        data=result["data"],
        mime_type=result["mime_type"],
        metadata=metadata,
        prefix="video",
    )

    return {
        "path": str(path),
        "enhanced_prompt": enhanced_prompt,
        "model": model,
        "warnings": [w.to_dict() for w in warnings],
    }
