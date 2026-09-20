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
from .io_utils import atomic_write_json

logger = logging.getLogger(__name__)

# Depth cap for the upward profile search.
MAX_PARENT_WALK = 40

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
    "reference_image": "",
}


def find_profile(cwd: str) -> Optional[Path]:
    """Search up the directory tree for a style profile.

    Returns the path to the profile file, or None if not found.
    """
    current = Path(cwd).resolve()
    home = Path.home().resolve()
    for _ in range(MAX_PARENT_WALK):
        profile_path = current / STYLE_PROFILE_FILENAME
        if profile_path.is_file():
            return profile_path
        # Stop at the repo boundary. Walking past it used to pick up a stray
        # profile in $HOME and inject it into every unrelated project.
        if (current / ".git").exists() or current == home:
            return None
        parent = current.parent
        if parent == current:
            return None
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
    reference_image: str = "",
) -> Path:
    """Create a new style profile in the target directory."""
    profile = dict(DEFAULT_PROFILE)
    profile["project_type"] = project_type
    profile["framework"] = framework
    profile["design_system"] = design_system
    profile["default_aspect_ratio"] = aspect_ratio
    profile["default_resolution"] = resolution
    profile["reference_image"] = reference_image

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

    # "Create or update": preserve fields the user hand-edited that we were
    # not asked to change, instead of rebuilding from DEFAULT_PROFILE.
    if path.is_file():
        try:
            with open(path) as f:
                existing = json.load(f)
            if isinstance(existing, dict):
                merged = {
                    **existing,
                    **{k: v for k, v in profile.items() if v not in ("", {}, None)},
                }
                for nested in ("colors", "typography"):
                    if isinstance(existing.get(nested), dict):
                        merged[nested] = {**existing[nested], **profile.get(nested, {})}
                profile = merged
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not merge existing profile at %s: %s", path, e)

    atomic_write_json(path, profile)
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

    atomic_write_json(path, profile)
    return path


# Directories never worth scanning for a project's own design tokens.
SCAN_EXCLUDE = {
    "node_modules",
    ".git",
    ".next",
    "dist",
    "build",
    ".venv",
    "venv",
    "vendor",
    "__pycache__",
    ".turbo",
    "coverage",
    "out",
}
MAX_SCAN_FILES = 50
MAX_SCAN_BYTES = 512 * 1024


def _iter_css_files(project_dir: Path):
    """Yield up to MAX_SCAN_FILES css files, skipping vendored trees."""
    seen: set[Path] = set()
    count = 0
    for css_glob in ("*.css", "src/**/*.css", "app/**/*.css", "styles/**/*.css"):
        for css_file in project_dir.glob(css_glob):
            if count >= MAX_SCAN_FILES:
                return
            resolved = css_file.resolve()
            if resolved in seen:
                continue
            if SCAN_EXCLUDE & set(css_file.parts):
                continue
            try:
                if css_file.stat().st_size > MAX_SCAN_BYTES:
                    continue
            except OSError:
                continue
            seen.add(resolved)
            count += 1
            yield css_file


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

    # Detect CSS custom properties, fonts, and dark mode in a SINGLE pass.
    # This used to glob and fully read every CSS file twice.
    for css_file in _iter_css_files(project_dir):
        try:
            css_content = css_file.read_text(errors="replace")
        except OSError:
            continue

        # Look for --color-primary or --primary-color patterns
        css_vars = re.findall(r"--(?:color-)?(\w+)(?:-color)?:\s*(#[0-9a-fA-F]{3,8})", css_content)
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

        fonts = re.findall(r"font-family:\s*['\"]?([^;'\"]+)", css_content)
        if fonts:
            detected["typography"]["heading_font"] = fonts[0].split(",")[0].strip("'\" ")

        if "prefers-color-scheme: dark" in css_content:
            if "dark" not in detected["visual_style"]:
                detected["visual_style"] += ", dark mode support"

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
