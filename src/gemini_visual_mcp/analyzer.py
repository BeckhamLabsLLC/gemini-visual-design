"""Design analysis with multimodal input.

Analyzes screenshots or generated images to provide structured design
critique with actionable improvement suggestions. Suggestions are formatted
as edit_image-compatible instructions for direct follow-up.
"""

import json
import logging

from .gemini_client import GeminiClient
from .image_utils import read_image

logger = logging.getLogger(__name__)

# Structured analysis prompts per focus area
ANALYSIS_PROMPTS = {
    "color": """\
Analyze the color usage in this design image. Return a JSON object with:
{{
  "score": <1-10>,
  "palette_detected": ["#hex1", "#hex2", ...],
  "issues": [
    {{"issue": "description", "severity": "high|medium|low", "edit_instruction": "specific edit instruction to fix this"}}
  ],
  "strengths": ["what works well"],
  "suggestions": ["actionable improvement"]
}}

Focus on: contrast ratios, color harmony, accessibility (WCAG), brand consistency, emotional tone.
{project_context}
Return ONLY valid JSON.""",
    "layout": """\
Analyze the layout and composition of this design image. Return a JSON object with:
{{
  "score": <1-10>,
  "layout_type": "detected layout pattern",
  "issues": [
    {{"issue": "description", "severity": "high|medium|low", "edit_instruction": "specific edit instruction to fix this"}}
  ],
  "strengths": ["what works well"],
  "suggestions": ["actionable improvement"]
}}

Focus on: visual hierarchy, alignment, spacing consistency, grid usage, content density, responsive considerations.
{project_context}
Return ONLY valid JSON.""",
    "typography": """\
Analyze the typography in this design image. Return a JSON object with:
{{
  "score": <1-10>,
  "fonts_detected": ["font descriptions"],
  "issues": [
    {{"issue": "description", "severity": "high|medium|low", "edit_instruction": "specific edit instruction to fix this"}}
  ],
  "strengths": ["what works well"],
  "suggestions": ["actionable improvement"]
}}

Focus on: readability, font pairing, hierarchy (heading/body/caption sizes), line height, letter spacing, text contrast.
{project_context}
Return ONLY valid JSON.""",
    "overall": """\
Provide a comprehensive design analysis of this image. Return a JSON object with:
{{
  "overall_score": <1-10>,
  "categories": {{
    "color": {{"score": <1-10>, "summary": "brief assessment"}},
    "layout": {{"score": <1-10>, "summary": "brief assessment"}},
    "typography": {{"score": <1-10>, "summary": "brief assessment"}},
    "usability": {{"score": <1-10>, "summary": "brief assessment"}}
  }},
  "top_issues": [
    {{"issue": "description", "category": "color|layout|typography|usability", "severity": "high|medium|low", "edit_instruction": "specific edit instruction to fix this"}}
  ],
  "strengths": ["what works well"],
  "priority_improvements": ["most impactful changes, ordered by impact"]
}}

{project_context}
Return ONLY valid JSON.""",
}

# Project-type-specific context
PROJECT_CONTEXT = {
    "game": (
        "This is a game interface/asset. Consider: readability at game resolution, "
        "visual feedback clarity, information density for gameplay, "
        "art style consistency, and platform conventions."
    ),
    "landing-page": (
        "This is a landing page design. Consider: above-the-fold impact, "
        "CTA visibility and hierarchy, trust signals, scanning patterns, "
        "conversion-focused layout, and mobile responsiveness."
    ),
    "web-app": (
        "This is a web application interface. Consider: information architecture, "
        "navigation clarity, action hierarchy, data density, "
        "consistency with common UI patterns, and accessibility."
    ),
    "general": "Analyze this as a general design piece.",
}


async def analyze_design(
    client: GeminiClient,
    image_path: str,
    focus: str = "overall",
    project_type: str = "general",
) -> dict:
    """Analyze a design image and return structured critique.

    Args:
        client: GeminiClient instance
        image_path: Path to the image to analyze
        focus: Analysis focus ("color", "layout", "typography", "overall")
        project_type: Project context ("game", "landing-page", "web-app", "general")

    Returns:
        Dict with scored categories, issues, and actionable suggestions.
        Each issue includes an edit_instruction that can be fed to edit_image.
    """
    if focus not in ANALYSIS_PROMPTS:
        raise ValueError(f"Unknown focus: {focus}. Choose from: {list(ANALYSIS_PROMPTS.keys())}")

    image_data, mime_type = read_image(image_path)

    project_context = PROJECT_CONTEXT.get(project_type, PROJECT_CONTEXT["general"])
    analysis_prompt = ANALYSIS_PROMPTS[focus].format(project_context=project_context)

    raw_response = await client.analyze_image(
        image_data=image_data,
        mime_type=mime_type,
        analysis_prompt=analysis_prompt,
    )

    # Parse JSON from response
    try:
        # Try to extract JSON from the response (model may wrap it in markdown)
        json_str = raw_response.strip()
        if json_str.startswith("```"):
            # Remove markdown code fence
            lines = json_str.split("\n")
            json_lines = []
            in_fence = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    json_lines.append(line)
            json_str = "\n".join(json_lines)

        analysis = json.loads(json_str)
    except json.JSONDecodeError:
        # Return raw text if JSON parsing fails
        analysis = {
            "raw_analysis": raw_response,
            "parse_error": "Could not parse structured analysis. Raw text returned.",
        }

    analysis["image_path"] = image_path
    analysis["focus"] = focus
    analysis["project_type"] = project_type

    return analysis
