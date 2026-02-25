"""Per-project style profile management.

Manages .gemini-design-profile.json files that store color palette,
typography, design system, and style preferences for consistent generation.
"""

import json
import logging
import re
from pathlib import Path
from typing import Optional

from .config import STYLE_PROFILE_FILENAME

logger = logging.getLogger(__name__)

DEFAULT_PROFILE = {
    "project_type": "web-app",
    "framework": "",
    "design_system": "custom",
    "colors": {
        "primary": "#3b82f6",
        "secondary": "#8b5cf6",
        "background": "#ffffff",
        "surface": "#f8fafc",
        "text": "#0f172a",
    },
    "typography": {
        "style": "modern sans-serif",
        "heading_font": "",
        "body_font": "",
    },
    "visual_style": "clean, minimal",
    "icon_style": "outlined, 24px",
    "image_style": "modern illustrations",
    "default_aspect_ratio": "16:9",
    "default_resolution": "1K",
}


def find_profile(cwd: str) -> Optional[Path]:
    """Search up the directory tree for a style profile.

    Returns the path to the profile file, or None if not found.
    """
    current = Path(cwd).resolve()
    while True:
        profile_path = current / STYLE_PROFILE_FILENAME
        if profile_path.is_file():
            return profile_path
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def load_profile(cwd: str) -> Optional[dict]:
    """Load the project's style profile, if one exists."""
    path = find_profile(cwd)
    if path is None:
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load style profile at {path}: {e}")
        return None


def create_profile(
    target_dir: str,
    project_type: str = "web-app",
    colors: Optional[dict] = None,
    typography: Optional[dict] = None,
    visual_style: str = "",
    framework: str = "",
    design_system: str = "custom",
    icon_style: str = "",
    image_style: str = "",
    aspect_ratio: str = "16:9",
    resolution: str = "1K",
) -> Path:
    """Create a new style profile in the target directory."""
    profile = dict(DEFAULT_PROFILE)
    profile["project_type"] = project_type
    profile["framework"] = framework
    profile["design_system"] = design_system
    profile["default_aspect_ratio"] = aspect_ratio
    profile["default_resolution"] = resolution

    if colors:
        profile["colors"] = {**profile["colors"], **colors}
    if typography:
        profile["typography"] = {**profile["typography"], **typography}
    if visual_style:
        profile["visual_style"] = visual_style
    if icon_style:
        profile["icon_style"] = icon_style
    if image_style:
        profile["image_style"] = image_style

    path = Path(target_dir) / STYLE_PROFILE_FILENAME
    with open(path, "w") as f:
        json.dump(profile, f, indent=2)
        f.write("\n")

    logger.info(f"Created style profile at {path}")
    return path


def update_profile(cwd: str, updates: dict) -> Optional[Path]:
    """Update an existing style profile with new values.

    Performs a shallow merge — top-level keys are replaced, nested dicts
    like 'colors' and 'typography' are merged.
    """
    path = find_profile(cwd)
    if path is None:
        return None

    profile = load_profile(cwd)
    if profile is None:
        return None

    for key, value in updates.items():
        if key in ("colors", "typography") and isinstance(value, dict):
            existing = profile.get(key, {})
            if isinstance(existing, dict):
                existing.update(value)
                profile[key] = existing
            else:
                profile[key] = value
        else:
            profile[key] = value

    with open(path, "w") as f:
        json.dump(profile, f, indent=2)
        f.write("\n")

    return path


def auto_detect_profile(cwd: str) -> dict:
    """Scan existing project files to pre-fill a style profile.

    Looks at tailwind.config.js/ts, CSS variables, package.json to infer
    colors, framework, typography, and design system.
    """
    detected = dict(DEFAULT_PROFILE)
    project_dir = Path(cwd)

    # Detect framework from package.json
    pkg_json = project_dir / "package.json"
    if pkg_json.is_file():
        try:
            with open(pkg_json) as f:
                pkg = json.load(f)
            deps = {}
            deps.update(pkg.get("dependencies", {}))
            deps.update(pkg.get("devDependencies", {}))

            frameworks = []
            if "react" in deps or "react-dom" in deps:
                frameworks.append("React")
            if "next" in deps:
                frameworks.append("Next.js")
            if "vue" in deps:
                frameworks.append("Vue")
            if "svelte" in deps or "@sveltejs/kit" in deps:
                frameworks.append("Svelte")
            if "tailwindcss" in deps:
                frameworks.append("Tailwind CSS")
            if "@mui/material" in deps:
                detected["design_system"] = "Material UI"
            if "@chakra-ui/react" in deps:
                detected["design_system"] = "Chakra UI"
            if "antd" in deps:
                detected["design_system"] = "Ant Design"

            if frameworks:
                detected["framework"] = " + ".join(frameworks)
        except (json.JSONDecodeError, OSError):
            pass

    # Detect colors from tailwind.config
    for tw_file in ["tailwind.config.js", "tailwind.config.ts", "tailwind.config.mjs"]:
        tw_path = project_dir / tw_file
        if tw_path.is_file():
            try:
                with open(tw_path) as f:
                    tw_content = f.read()
                # Extract hex colors
                hex_colors = re.findall(r"['\"]#([0-9a-fA-F]{6})['\"]", tw_content)
                if hex_colors:
                    color_keys = ["primary", "secondary", "background", "surface", "text"]
                    for i, color in enumerate(hex_colors[:5]):
                        if i < len(color_keys):
                            detected["colors"][color_keys[i]] = f"#{color}"
            except OSError:
                pass
            break

    # Detect CSS custom properties
    for css_glob in ["*.css", "src/**/*.css", "app/**/*.css", "styles/**/*.css"]:
        for css_file in project_dir.glob(css_glob):
            try:
                with open(css_file) as f:
                    css_content = f.read()
                # Look for --color-primary or --primary-color patterns
                css_vars = re.findall(
                    r"--(?:color-)?(\w+)(?:-color)?:\s*(#[0-9a-fA-F]{3,8})", css_content
                )
                for name, value in css_vars:
                    name_lower = name.lower()
                    if "primary" in name_lower:
                        detected["colors"]["primary"] = value
                    elif "secondary" in name_lower:
                        detected["colors"]["secondary"] = value
                    elif "background" in name_lower or "bg" in name_lower:
                        detected["colors"]["background"] = value
                    elif "surface" in name_lower:
                        detected["colors"]["surface"] = value
                    elif "text" in name_lower or "foreground" in name_lower:
                        detected["colors"]["text"] = value

                # Detect font families
                fonts = re.findall(r"font-family:\s*['\"]?([^;'\"]+)", css_content)
                if fonts:
                    detected["typography"]["heading_font"] = fonts[0].split(",")[0].strip("'\" ")
            except OSError:
                pass

    # Detect dark mode
    for css_glob in ["*.css", "src/**/*.css", "app/**/*.css"]:
        for css_file in project_dir.glob(css_glob):
            try:
                with open(css_file) as f:
                    content = f.read()
                if "prefers-color-scheme: dark" in content or "dark" in content.lower():
                    if "dark" not in detected["visual_style"]:
                        detected["visual_style"] += ", dark mode support"
                    break
            except OSError:
                pass

    return detected


def apply_to_prompt(profile: dict, prompt: str) -> str:
    """Inject style context from profile into a prompt.

    Appends color palette, typography, framework, and design system
    information to the prompt for consistent generation.
    """
    context_parts = []

    # Colors
    colors = profile.get("colors", {})
    if colors:
        color_str = ", ".join(f"{k}: {v}" for k, v in colors.items() if v)
        if color_str:
            context_parts.append(f"Color palette: {color_str}")

    # Typography
    typography = profile.get("typography", {})
    style = typography.get("style", "")
    heading = typography.get("heading_font", "")
    body = typography.get("body_font", "")
    type_parts = []
    if style:
        type_parts.append(style)
    if heading:
        type_parts.append(f"headings in {heading}")
    if body and body != heading:
        type_parts.append(f"body in {body}")
    if type_parts:
        context_parts.append(f"Typography: {', '.join(type_parts)}")

    # Framework
    framework = profile.get("framework", "")
    if framework:
        context_parts.append(f"Framework: {framework}")

    # Design system
    design_system = profile.get("design_system", "")
    if design_system and design_system != "custom":
        context_parts.append(f"Design system: {design_system}")

    # Visual style
    visual_style = profile.get("visual_style", "")
    if visual_style:
        context_parts.append(f"Visual style: {visual_style}")

    # Icon style (if relevant)
    icon_style = profile.get("icon_style", "")
    if icon_style and ("icon" in prompt.lower() or "ui" in prompt.lower()):
        context_parts.append(f"Icon style: {icon_style}")

    if not context_parts:
        return prompt

    context_block = "\n".join(f"- {part}" for part in context_parts)
    return f"{prompt}\n\nProject design context:\n{context_block}"
