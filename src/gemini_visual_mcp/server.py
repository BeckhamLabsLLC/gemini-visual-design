"""MCP Server for Gemini Visual Design.

Provides 9 tools for image generation, editing, video creation,
design analysis, and asset management — all enhanced by the prompt
engine and project style profiles to minimize wasted API calls.
"""

import asyncio
import json
import logging
import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .analyzer import analyze_design
from .asset_manager import (
    cleanup_old,
    get_preview_dir,
    list_generated,
    save_to_project,
)
from .config import (
    ANALYSIS_FOCUS_AREAS,
    ASPECT_RATIOS,
    MODEL_CHOICES_IMAGE,
    MODEL_CHOICES_VIDEO,
    PROJECT_TYPES,
    TEMPLATE_CATEGORIES,
    TOKEN_FORMATS,
)
from .gemini_client import GeminiClient, GeminiClientError
from .image_edit import edit_image
from .image_gen import auto_generate
from .prompt_engine import (
    PromptValidationError,
    get_templates,
)
from .style_profile import (
    auto_detect_profile,
    create_profile,
    load_profile,
)
from .video_gen import generate_video

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GeminiVisualDesignServer:
    """MCP Server for visual design with Gemini."""

    def __init__(self):
        self._server = Server("gemini-visual-design")
        self._client = None
        self._setup_handlers()

    def _get_client(self) -> GeminiClient:
        """Lazy-init the Gemini client."""
        if self._client is None:
            self._client = GeminiClient()
        return self._client

    def _cwd(self) -> str:
        """Get the current working directory."""
        return os.environ.get("PROJECT_DIR", os.getcwd())

    def _setup_handlers(self):
        """Register all MCP tool handlers."""

        @self._server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="generate_image",
                    description=(
                        "Generate images from text prompts, enhanced by the prompt engine "
                        "and project style profile. Supports Gemini (fast drafts) and "
                        "Imagen 4 (high quality finals). Use templates for proven prompt structures."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Description of the image to generate",
                            },
                            "template": {
                                "type": "string",
                                "description": (
                                    "Optional template as 'category/key' (e.g., 'ui-mockups/dashboard'). "
                                    "Use get_prompt_templates to see available templates."
                                ),
                            },
                            "model": {
                                "type": "string",
                                "enum": MODEL_CHOICES_IMAGE,
                                "default": "auto",
                                "description": (
                                    "Model selection: 'gemini' (fast drafts), "
                                    "'imagen' (high quality), 'auto' (smart selection)"
                                ),
                            },
                            "aspect_ratio": {
                                "type": "string",
                                "enum": ASPECT_RATIOS,
                                "default": "16:9",
                                "description": "Image aspect ratio",
                            },
                            "count": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 4,
                                "default": 1,
                                "description": "Number of images to generate (Imagen only)",
                            },
                            "use_profile": {
                                "type": "boolean",
                                "default": True,
                                "description": "Apply project style profile to the prompt",
                            },
                        },
                        "required": ["prompt"],
                    },
                ),
                Tool(
                    name="edit_image",
                    description=(
                        "Edit an existing image with natural language instructions. "
                        "Preferred over regenerating — builds on previous results. "
                        "Keeps the original file intact."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "image_path": {
                                "type": "string",
                                "description": "Path to the image to edit",
                            },
                            "instruction": {
                                "type": "string",
                                "description": "Natural language edit instruction (e.g., 'Change the button color to blue')",
                            },
                            "preserve_style": {
                                "type": "boolean",
                                "default": True,
                                "description": "Apply project style profile context to the edit",
                            },
                        },
                        "required": ["image_path", "instruction"],
                    },
                ),
                Tool(
                    name="analyze_design",
                    description=(
                        "Visual design critique with scored categories and actionable "
                        "improvement suggestions. Each suggestion includes an edit instruction "
                        "that can be fed directly to edit_image."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "image_path": {
                                "type": "string",
                                "description": "Path to the design image or screenshot to analyze",
                            },
                            "focus": {
                                "type": "string",
                                "enum": ANALYSIS_FOCUS_AREAS,
                                "default": "overall",
                                "description": "Analysis focus area",
                            },
                            "project_type": {
                                "type": "string",
                                "enum": PROJECT_TYPES,
                                "default": "general",
                                "description": "Project type for context-aware analysis",
                            },
                        },
                        "required": ["image_path"],
                    },
                ),
                Tool(
                    name="generate_video",
                    description=(
                        "Generate short video clips using Veo models. "
                        "Supports text-to-video and image-to-video with async polling."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Description of the video to generate",
                            },
                            "model": {
                                "type": "string",
                                "enum": MODEL_CHOICES_VIDEO,
                                "default": "veo-2",
                                "description": "Video model: 'veo-2' (stable), 'veo-3.1' (latest), 'veo-3.1-fast'",
                            },
                            "reference_image": {
                                "type": "string",
                                "description": "Optional path to reference image for image-to-video",
                            },
                        },
                        "required": ["prompt"],
                    },
                ),
                Tool(
                    name="save_asset",
                    description=(
                        "Save a generated asset from the temp preview directory "
                        "to your project directory."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "temp_path": {
                                "type": "string",
                                "description": "Path to the file in the preview directory",
                            },
                            "destination_dir": {
                                "type": "string",
                                "description": "Target directory in your project",
                            },
                            "filename": {
                                "type": "string",
                                "description": "Desired filename (e.g., 'hero-image.png')",
                            },
                        },
                        "required": ["temp_path", "destination_dir", "filename"],
                    },
                ),
                Tool(
                    name="list_generated",
                    description=(
                        "List all generated assets in the temp preview directory "
                        "with metadata (prompt, model, timestamp)."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
                Tool(
                    name="generate_design_tokens",
                    description=(
                        "Generate design system tokens (colors, typography, spacing) "
                        "from a description or reference image. Outputs as CSS, Tailwind, JSON, or SCSS."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "description": {
                                "type": "string",
                                "description": "Description of the desired design system (mood, brand, style)",
                            },
                            "reference_image": {
                                "type": "string",
                                "description": "Optional path to reference image to extract design tokens from",
                            },
                            "format": {
                                "type": "string",
                                "enum": TOKEN_FORMATS,
                                "default": "css",
                                "description": "Output format for design tokens",
                            },
                        },
                        "required": ["description"],
                    },
                ),
                Tool(
                    name="init_style_profile",
                    description=(
                        "Create or update the project's style profile. "
                        "Optionally auto-detects settings from existing CSS/Tailwind config."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_type": {
                                "type": "string",
                                "enum": ["game", "landing-page", "web-app"],
                                "description": "Type of project",
                            },
                            "auto_detect": {
                                "type": "boolean",
                                "default": True,
                                "description": "Scan existing CSS/config files to pre-fill the profile",
                            },
                            "colors": {
                                "type": "object",
                                "description": "Color overrides: {primary, secondary, background, surface, text}",
                            },
                            "typography": {
                                "type": "object",
                                "description": "Typography: {style, heading_font, body_font}",
                            },
                            "visual_style": {
                                "type": "string",
                                "description": "Visual style description (e.g., 'clean, minimal, dark mode')",
                            },
                            "framework": {
                                "type": "string",
                                "description": "Framework (e.g., 'React + Tailwind CSS')",
                            },
                            "design_system": {
                                "type": "string",
                                "description": "Design system (e.g., 'Material Design 3', 'custom')",
                            },
                        },
                        "required": ["project_type"],
                    },
                ),
                Tool(
                    name="get_prompt_templates",
                    description=(
                        "List available prompt templates by category. "
                        "Templates provide proven prompt structures for common design tasks."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "enum": TEMPLATE_CATEGORIES + ["all"],
                                "default": "all",
                                "description": "Template category to filter by",
                            },
                        },
                    },
                ),
            ]

        @self._server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            try:
                result = await self._handle_tool(name, arguments)
                return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
            except PromptValidationError as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e), "type": "validation"}, indent=2))]
            except GeminiClientError as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e), "type": "api_error"}, indent=2))]
            except FileNotFoundError as e:
                return [TextContent(type="text", text=json.dumps({"error": str(e), "type": "file_not_found"}, indent=2))]
            except Exception as e:
                logger.exception(f"Unexpected error in tool {name}")
                return [TextContent(type="text", text=json.dumps({"error": str(e), "type": "internal_error"}, indent=2))]

    async def _handle_tool(self, name: str, args: dict) -> Any:
        """Route tool calls to the appropriate handler."""

        if name == "generate_image":
            client = self._get_client()
            results = await auto_generate(
                client=client,
                prompt=args["prompt"],
                model=args.get("model", "auto"),
                count=args.get("count", 1),
                aspect_ratio=args.get("aspect_ratio", "16:9"),
                cwd=self._cwd(),
                use_profile=args.get("use_profile", True),
                template=args.get("template"),
            )
            # Clean up old previews on generation
            cleanup_old()
            return {
                "generated": [
                    {
                        "path": r["path"],
                        "model": r["model"],
                        "enhanced_prompt": r["enhanced_prompt"],
                        "warnings": r["warnings"],
                    }
                    for r in results
                ],
                "preview_dir": get_preview_dir(),
                "tip": "Use edit_image to refine, or save_asset to save to your project.",
            }

        elif name == "edit_image":
            client = self._get_client()
            result = await edit_image(
                client=client,
                image_path=args["image_path"],
                instruction=args["instruction"],
                cwd=self._cwd(),
                preserve_style=args.get("preserve_style", True),
            )
            return {
                "edited_path": result["path"],
                "original_path": result["original_path"],
                "instruction": result["instruction"],
                "model": result["model"],
                "tip": "Original preserved. Use edit_image again to further refine.",
            }

        elif name == "analyze_design":
            client = self._get_client()
            result = await analyze_design(
                client=client,
                image_path=args["image_path"],
                focus=args.get("focus", "overall"),
                project_type=args.get("project_type", "general"),
            )
            return result

        elif name == "generate_video":
            client = self._get_client()
            result = await generate_video(
                client=client,
                prompt=args["prompt"],
                model=args.get("model", "veo-2"),
                reference_image=args.get("reference_image"),
                cwd=self._cwd(),
            )
            return {
                "video_path": result["path"],
                "model": result["model"],
                "enhanced_prompt": result["enhanced_prompt"],
                "warnings": result["warnings"],
                "tip": "Use save_asset to save to your project.",
            }

        elif name == "save_asset":
            path = save_to_project(
                temp_path=args["temp_path"],
                dest_dir=args["destination_dir"],
                filename=args["filename"],
            )
            return {
                "saved_path": str(path),
                "success": True,
            }

        elif name == "list_generated":
            items = list_generated()
            return {
                "assets": items,
                "count": len(items),
                "preview_dir": get_preview_dir(),
            }

        elif name == "generate_design_tokens":
            client = self._get_client()
            return await self._generate_design_tokens(
                client,
                description=args["description"],
                reference_image=args.get("reference_image"),
                token_format=args.get("format", "css"),
            )

        elif name == "init_style_profile":
            return self._init_style_profile(
                project_type=args["project_type"],
                auto_detect=args.get("auto_detect", True),
                colors=args.get("colors"),
                typography=args.get("typography"),
                visual_style=args.get("visual_style"),
                framework=args.get("framework"),
                design_system=args.get("design_system"),
            )

        elif name == "get_prompt_templates":
            category = args.get("category", "all")
            templates = get_templates(category)
            return {
                "templates": templates,
                "count": len(templates),
                "usage": "Pass template as 'category/key' to generate_image (e.g., 'ui-mockups/dashboard')",
            }

        else:
            return {"error": f"Unknown tool: {name}"}

    async def _generate_design_tokens(
        self,
        client: GeminiClient,
        description: str,
        reference_image: str | None = None,
        token_format: str = "css",
    ) -> dict:
        """Generate design tokens from description or reference image."""
        prompt = f"""Generate a complete design system token set based on this description: {description}

Return the tokens in {token_format} format. Include:
- Color palette (primary, secondary, accent, background, surface, text, error, warning, success)
- Typography scale (font families, sizes for h1-h6, body, caption, overline)
- Spacing scale (4px base: xs, sm, md, lg, xl, 2xl)
- Border radius scale (none, sm, md, lg, full)
- Shadow scale (sm, md, lg)

Return ONLY the {token_format} code, no explanations."""

        if reference_image:
            from .image_utils import read_image

            try:
                img_data, mime = read_image(reference_image)
            except FileNotFoundError:
                img_data = None

            if img_data:
                prompt = f"""Analyze this reference image and extract a design token set. {description}

Return the tokens in {token_format} format. Include:
- Color palette extracted from the image (primary, secondary, accent, background, surface, text)
- Typography recommendations based on the visual style
- Spacing scale (4px base)
- Border radius and shadow scales

Return ONLY the {token_format} code, no explanations."""

                raw = await client.analyze_image(img_data, mime, prompt)
            else:
                raw = await client.generate_text(prompt)
        else:
            raw = await client.generate_text(prompt)

        # Clean up code fences
        tokens_code = raw.strip()
        if tokens_code.startswith("```"):
            lines = tokens_code.split("\n")
            clean_lines = []
            in_fence = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_fence = not in_fence
                    continue
                if in_fence:
                    clean_lines.append(line)
            tokens_code = "\n".join(clean_lines)

        # Update style profile with extracted colors if possible
        cwd = self._cwd()
        profile = load_profile(cwd)
        if profile:
            # Try to extract colors to update profile
            import re

            hex_colors = re.findall(r"#[0-9a-fA-F]{6}", tokens_code)
            if len(hex_colors) >= 3:
                from .style_profile import update_profile

                color_keys = ["primary", "secondary", "background", "surface", "text"]
                color_update = {}
                for i, color in enumerate(hex_colors[:5]):
                    if i < len(color_keys):
                        color_update[color_keys[i]] = color
                update_profile(cwd, {"colors": color_update})

        return {
            "tokens": tokens_code,
            "format": token_format,
            "description": description,
            "profile_updated": profile is not None,
        }

    def _init_style_profile(
        self,
        project_type: str,
        auto_detect: bool = True,
        colors: dict | None = None,
        typography: dict | None = None,
        visual_style: str | None = None,
        framework: str | None = None,
        design_system: str | None = None,
    ) -> dict:
        """Create or update the project style profile."""
        cwd = self._cwd()

        # Start with auto-detected values if requested
        if auto_detect:
            detected = auto_detect_profile(cwd)
        else:
            from .style_profile import DEFAULT_PROFILE

            detected = dict(DEFAULT_PROFILE)

        # Apply explicit overrides
        detected["project_type"] = project_type
        if colors:
            detected["colors"] = {**detected.get("colors", {}), **colors}
        if typography:
            detected["typography"] = {**detected.get("typography", {}), **typography}
        if visual_style:
            detected["visual_style"] = visual_style
        if framework:
            detected["framework"] = framework
        if design_system:
            detected["design_system"] = design_system

        # Create the profile
        path = create_profile(
            target_dir=cwd,
            project_type=detected["project_type"],
            colors=detected.get("colors"),
            typography=detected.get("typography"),
            visual_style=detected.get("visual_style", ""),
            framework=detected.get("framework", ""),
            design_system=detected.get("design_system", "custom"),
            icon_style=detected.get("icon_style", ""),
            image_style=detected.get("image_style", ""),
            aspect_ratio=detected.get("default_aspect_ratio", "16:9"),
            resolution=detected.get("default_resolution", "1K"),
        )

        return {
            "profile_path": str(path),
            "profile": detected,
            "auto_detected": auto_detect,
        }

    async def run(self):
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self._server.run(
                read_stream, write_stream, self._server.create_initialization_options()
            )


def main():
    """Entry point for the MCP server."""
    server = GeminiVisualDesignServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
