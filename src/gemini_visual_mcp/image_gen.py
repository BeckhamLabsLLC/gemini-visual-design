"""Image generation across the Gemini image tiers.

All generation routes through the prompt engine for enhancement before
hitting the API. Supports auto tier selection (draft vs final).
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from .asset_manager import save_generated
from .config import (
    DEFAULT_ASPECT_RATIO,
    DEFAULT_IMAGE_COUNT,
    DEFAULT_IMAGE_TIER,
    IMAGE_MODELS,
    MODEL_CHOICES_IMAGE,
    clamp_resolution,
    resolve_image_tier,
)
from .gemini_client import GeminiClient
from .image_utils import read_image
from .prompt_engine import PromptValidationWarning, enhance
from .style_profile import load_profile

logger = logging.getLogger(__name__)

# Prompt wording that means the user wants a final asset, not a draft.
QUALITY_WORDS = ("final", "production", "high quality", "polished", "publish", "hero image")

STYLE_REFERENCE_PREAMBLE = (
    "Use the provided image ONLY as a style and aesthetic reference. "
    "Do NOT reproduce or edit the reference image. Generate a completely "
    "new image matching its art style, color palette, rendering technique, "
    "and visual mood. The new image should depict: "
)


def _select_tier(prompt: str, template: Optional[str]) -> str:
    """Pick a tier for model='auto'.

    Auto never selects 'draft' - opting into the cheapest model should be a
    deliberate choice, not something inferred from prompt wording.
    """
    if template and "/" in template:
        from .prompt_engine import TEMPLATES

        cat, key = template.split("/", 1)
        recommended = TEMPLATES.get(cat, {}).get(key, {}).get("recommended_model")
        if recommended:
            tier, _ = resolve_image_tier(recommended)
            if tier in IMAGE_MODELS:
                return tier

    if any(word in prompt.lower() for word in QUALITY_WORDS):
        return "pro"
    return DEFAULT_IMAGE_TIER


async def generate_images(
    client: GeminiClient,
    prompt: str,
    tier: str = DEFAULT_IMAGE_TIER,
    count: int = DEFAULT_IMAGE_COUNT,
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    resolution: Optional[str] = None,
    cwd: str = ".",
    use_profile: bool = True,
    template: Optional[str] = None,
    reference_image: Optional[str] = None,
    extra_warnings: Optional[list] = None,
) -> list[dict]:
    """Generate `count` images with the given tier.

    The Gemini image models reject candidate_count > 1, so count fans out to
    that many separate API calls. Partial success is preserved: images already
    paid for are returned even if a sibling call fails.

    Returns list of dicts with: path, enhanced_prompt, warnings, model, metadata
    """
    profile = load_profile(cwd) if use_profile else None

    # Auto-load reference image from profile if none provided explicitly
    if not reference_image and profile and profile.get("reference_image"):
        ref_path = profile["reference_image"]
        if Path(ref_path).is_file():
            reference_image = ref_path

    enhanced_prompt, warnings = enhance(prompt, profile=profile, template=template)
    warnings = list(warnings) + list(extra_warnings or [])

    resolution, clamp_warning = clamp_resolution(tier, resolution)
    if clamp_warning:
        logger.info(clamp_warning)

    ref_data = None
    ref_mime = None
    if reference_image:
        ref_data, ref_mime = read_image(reference_image)
        enhanced_prompt = STYLE_REFERENCE_PREAMBLE + enhanced_prompt

    count = max(1, min(int(count or 1), 4))
    calls = [
        client.generate_image_gemini(
            prompt=enhanced_prompt,
            tier=tier,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            reference_image_data=ref_data,
            reference_mime_type=ref_mime,
        )
        for _ in range(count)
    ]
    outcomes = await asyncio.gather(*calls, return_exceptions=True)

    failures = [o for o in outcomes if isinstance(o, BaseException)]
    results = [r for o in outcomes if not isinstance(o, BaseException) for r in o]

    if not results:
        # Every call failed - surface the first real error rather than an
        # empty list the caller has to guess about.
        raise failures[0]

    if failures:
        logger.warning("%d of %d image calls failed: %s", len(failures), count, failures[0])

    warning_dicts = [w.to_dict() for w in warnings]
    if clamp_warning:
        warning_dicts.append({"type": "resolution_clamped", "message": clamp_warning})
    if failures:
        warning_dicts.append(
            {
                "type": "partial_failure",
                "message": f"{len(failures)} of {count} images failed: {failures[0]}",
            }
        )

    saved = []
    for result in results:
        model_used = result.get("model") or IMAGE_MODELS[tier]
        metadata = {
            "prompt": prompt,
            "enhanced_prompt": enhanced_prompt,
            "model": model_used,
            "tier": tier,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "template": template or "",
            "reference_image": reference_image or "",
            "warnings": warning_dicts,
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
                "warnings": warning_dicts,
                "model": model_used,
                "tier": tier,
                "text": result.get("text"),
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
    resolution: Optional[str] = None,
    cwd: str = ".",
    use_profile: bool = True,
    template: Optional[str] = None,
    reference_image: Optional[str] = None,
) -> list[dict]:
    """Generate with automatic tier selection.

    - "draft": cheapest, for throwaway iteration
    - "fast":  default
    - "pro":   finals - legible text, best fidelity
    - "auto":  'pro' when the prompt or template asks for a final, else 'fast'

    Every tier accepts a reference image, so unlike the retired Imagen path
    there is no tier that a reference image forces us away from.
    """
    tier, alias_warning = resolve_image_tier(model)

    extra = []
    if alias_warning:
        logger.info(alias_warning)
        extra.append(
            PromptValidationWarning(
                alias_warning,
                f"Use one of: {', '.join(MODEL_CHOICES_IMAGE)}.",
            )
        )

    if tier == "auto":
        tier = _select_tier(prompt, template)

    return await generate_images(
        client,
        prompt,
        tier=tier,
        count=count,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        cwd=cwd,
        use_profile=use_profile,
        template=template,
        reference_image=reference_image,
        extra_warnings=extra,
    )
