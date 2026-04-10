"""Image generation using Gemini native and Imagen 4.

All generation routes through the prompt engine for enhancement before
hitting the API. Supports auto model selection (draft vs final).
"""

import logging
from pathlib import Path
from typing import Optional

from .asset_manager import save_generated
from .config import DEFAULT_ASPECT_RATIO, DEFAULT_IMAGE_COUNT
from .gemini_client import GeminiClient
from .image_utils import read_image
from .prompt_engine import enhance
from .style_profile import load_profile

logger = logging.getLogger(__name__)


async def generate_with_gemini(
    client: GeminiClient,
    prompt: str,
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    cwd: str = ".",
    use_profile: bool = True,
    template: Optional[str] = None,
    reference_image: Optional[str] = None,
) -> list[dict]:
    """Generate image(s) using Gemini 2.5 Flash (fast, iterative drafts).

    When reference_image is provided, the model receives the image alongside
    the prompt and is instructed to match its art style in the new generation.

    Returns list of dicts with: path, enhanced_prompt, warnings, model, metadata
    """
    # Load profile
    profile = load_profile(cwd) if use_profile else None

    # Auto-load reference image from profile if none provided explicitly
    if not reference_image and profile and profile.get("reference_image"):
        ref_path = profile["reference_image"]
        if Path(ref_path).is_file():
            reference_image = ref_path

    # Enhance prompt
    enhanced_prompt, warnings = enhance(prompt, profile=profile, template=template)

    # Build style-reference prompt and read image bytes when a reference is provided
    ref_data = None
    ref_mime = None
    if reference_image:
        ref_data, ref_mime = read_image(reference_image)
        enhanced_prompt = (
            "Use the provided image ONLY as a style and aesthetic reference. "
            "Do NOT reproduce or edit the reference image. Generate a completely "
            "new image matching its art style, color palette, rendering technique, "
            "and visual mood. The new image should depict: " + enhanced_prompt
        )

    # Generate
    results = await client.generate_image_gemini(
        prompt=enhanced_prompt,
        aspect_ratio=aspect_ratio,
        reference_image_data=ref_data,
        reference_mime_type=ref_mime,
    )

    # Save results
    saved = []
    for i, result in enumerate(results):
        metadata = {
            "prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
            "model": "gemini-2.5-flash-image",
            "aspect_ratio": aspect_ratio,
            "template": template or "",
            "reference_image": reference_image or "",
            "warnings": [w.to_dict() for w in warnings],
        }

        path = save_generated(
            data=result["data"],
            mime_type=result["mime_type"],
            metadata=metadata,
            prefix="gen",
        )

        saved.append(
            {
                "path": str(path),
                "enhanced_prompt": enhanced_prompt,
                "warnings": [w.to_dict() for w in warnings],
                "model": "gemini-2.5-flash-image",
                "text": result.get("text"),
                "metadata": metadata,
            }
        )

    return saved


async def generate_with_imagen(
    client: GeminiClient,
    prompt: str,
    count: int = DEFAULT_IMAGE_COUNT,
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    cwd: str = ".",
    use_profile: bool = True,
    template: Optional[str] = None,
) -> list[dict]:
    """Generate image(s) using Imagen 4 (high quality, final assets).

    Returns list of dicts with: path, enhanced_prompt, warnings, model, metadata
    """
    # Load profile
    profile = load_profile(cwd) if use_profile else None

    # Enhance prompt
    enhanced_prompt, warnings = enhance(prompt, profile=profile, template=template)

    # Generate
    results = await client.generate_image_imagen(
        prompt=enhanced_prompt,
        count=count,
        aspect_ratio=aspect_ratio,
    )

    # Save results
    saved = []
    for i, result in enumerate(results):
        metadata = {
            "prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
            "model": "imagen-4.0",
            "aspect_ratio": aspect_ratio,
            "count": count,
            "template": template or "",
            "warnings": [w.to_dict() for w in warnings],
        }

        path = save_generated(
            data=result["data"],
            mime_type=result["mime_type"],
            metadata=metadata,
            prefix="gen",
        )

        saved.append(
            {
                "path": str(path),
                "enhanced_prompt": enhanced_prompt,
                "warnings": [w.to_dict() for w in warnings],
                "model": "imagen-4.0",
                "metadata": metadata,
            }
        )

    return saved


async def auto_generate(
    client: GeminiClient,
    prompt: str,
    model: str = "auto",
    count: int = DEFAULT_IMAGE_COUNT,
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    cwd: str = ".",
    use_profile: bool = True,
    template: Optional[str] = None,
    reference_image: Optional[str] = None,
) -> list[dict]:
    """Generate with automatic model selection.

    - "gemini": Use Gemini Flash (fast drafts, iterative editing)
    - "imagen": Use Imagen 4 (high quality finals)
    - "auto": Use Gemini for drafts, Imagen for production-quality assets

    When reference_image is provided, the Gemini path is always used
    (Imagen's text-to-image API does not accept reference images).

    Auto logic: Use Gemini by default. Use Imagen when:
    - User explicitly says "final", "production", "high quality", "polished"
    - Template recommends Imagen
    """
    # Reference images require Gemini — Imagen doesn't support image input for generation
    if reference_image:
        if model == "imagen":
            logger.warning(
                "Reference image provided with model='imagen'. "
                "Falling back to Gemini (Imagen does not support reference images)."
            )
        return await generate_with_gemini(
            client, prompt, aspect_ratio, cwd, use_profile, template, reference_image
        )

    if model == "imagen":
        return await generate_with_imagen(
            client, prompt, count, aspect_ratio, cwd, use_profile, template
        )

    if model == "gemini":
        return await generate_with_gemini(
            client, prompt, aspect_ratio, cwd, use_profile, template
        )

    # Auto selection
    use_imagen = False

    # Check if template recommends Imagen
    if template and "/" in template:
        from .prompt_engine import TEMPLATES

        cat, key = template.split("/", 1)
        tmpl = TEMPLATES.get(cat, {}).get(key, {})
        if tmpl.get("recommended_model") == "imagen":
            use_imagen = True

    # Check prompt for quality indicators
    quality_words = ["final", "production", "high quality", "polished", "publish", "hero image"]
    if any(word in prompt.lower() for word in quality_words):
        use_imagen = True

    if use_imagen:
        return await generate_with_imagen(
            client, prompt, count, aspect_ratio, cwd, use_profile, template
        )
    else:
        return await generate_with_gemini(
            client, prompt, aspect_ratio, cwd, use_profile, template
        )
