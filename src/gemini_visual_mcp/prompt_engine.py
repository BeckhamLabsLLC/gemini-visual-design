"""Prompt enhancement engine — the anti-waste core.

Every user prompt passes through validation, enrichment, and structuring
before hitting the Gemini API. This prevents wasted generations from
vague, poorly structured, or anti-pattern prompts.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

# Common negative phrases that should be rephrased positively
NEGATIVE_PATTERNS = [
    (r"\bno (\w+)", "Instead of 'no {0}', describe what IS there (e.g., 'empty {0}' or 'without {0}')"),
    (r"\bdon't\b", "Rephrase without 'don't' — describe the desired result positively"),
    (r"\bnot (\w+)", "Instead of 'not {0}', describe what you DO want"),
    (r"\bwithout any\b", "Consider describing the desired state instead of exclusions"),
    (r"\bnever\b", "Rephrase positively — describe the intended appearance"),
]


class PromptValidationWarning:
    """A non-fatal warning about prompt quality."""

    def __init__(self, message: str, suggestion: str):
        self.message = message
        self.suggestion = suggestion

    def to_dict(self) -> dict:
        return {"warning": self.message, "suggestion": self.suggestion}


class PromptValidationError(Exception):
    """Fatal validation error — prompt should not be sent to API."""

    pass


def validate(prompt: str) -> list[PromptValidationWarning]:
    """Validate a prompt and return warnings.

    Raises PromptValidationError for prompts that would definitely waste an API call.
    Returns a list of warnings for prompts that could be improved.
    """
    warnings = []

    if not prompt or not prompt.strip():
        raise PromptValidationError("Prompt is empty. Provide a description of what to generate.")

    stripped = prompt.strip()

    if len(stripped) < 10:
        raise PromptValidationError(
            f"Prompt is too short ({len(stripped)} chars). "
            "Provide a more detailed description to get useful results. "
            "Example: 'A modern dashboard with dark theme, showing analytics charts and a sidebar navigation'"
        )

    # Check for negative phrasing
    for pattern, suggestion_template in NEGATIVE_PATTERNS:
        match = re.search(pattern, stripped, re.IGNORECASE)
        if match:
            groups = match.groups()
            suggestion = suggestion_template.format(*groups) if groups else suggestion_template
            warnings.append(
                PromptValidationWarning(
                    f"Negative phrasing detected: '{match.group()}'",
                    suggestion,
                )
            )

    # Check for extremely generic prompts
    generic_terms = ["a thing", "something", "stuff", "make it good", "make it nice"]
    for term in generic_terms:
        if term in stripped.lower():
            warnings.append(
                PromptValidationWarning(
                    f"Vague term detected: '{term}'",
                    "Be specific about what you want — describe the subject, style, composition, and mood",
                )
            )

    return warnings


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, dict[str, dict]] = {
    "ui-mockups": {
        "dashboard": {
            "name": "Dashboard",
            "description": "Analytics dashboard with charts, metrics, and navigation",
            "skeleton": (
                "A professional {style} dashboard UI mockup. "
                "The layout includes a left sidebar navigation with icons, "
                "a top header bar with user avatar and notifications, "
                "and a main content area with {content}. "
                "{color_context}. Clean, modern interface design."
            ),
            "placeholders": {
                "style": "dark-themed",
                "content": "KPI metric cards across the top, a large line chart in the center, and a data table below",
                "color_context": "Use a dark background with accent color highlights for interactive elements",
            },
            "aspect_ratio": "16:9",
            "resolution": "1K",
            "recommended_model": "gemini",
        },
        "settings-page": {
            "name": "Settings Page",
            "description": "Application settings page with grouped options",
            "skeleton": (
                "A clean {style} settings page UI mockup. "
                "Organized into sections: {sections}. "
                "Each section has a heading and grouped controls. "
                "{color_context}. Toggle switches, dropdowns, and text inputs."
            ),
            "placeholders": {
                "style": "minimal",
                "sections": "Profile, Notifications, Privacy, Appearance",
                "color_context": "Clean white background with subtle dividers between sections",
            },
            "aspect_ratio": "16:9",
            "resolution": "1K",
            "recommended_model": "gemini",
        },
        "login-signup": {
            "name": "Login / Signup",
            "description": "Authentication page with form and branding",
            "skeleton": (
                "A {style} login and signup page UI mockup. "
                "Split layout with {left_side} on the left and "
                "a centered authentication form on the right. "
                "The form includes email field, password field, "
                "{auth_options}. {color_context}."
            ),
            "placeholders": {
                "style": "modern, polished",
                "left_side": "a branded illustration or gradient with the app logo",
                "auth_options": "social login buttons (Google, GitHub), and a 'Forgot password' link",
                "color_context": "Brand colors with high contrast for form inputs",
            },
            "aspect_ratio": "16:9",
            "resolution": "1K",
            "recommended_model": "gemini",
        },
        "ecommerce-product": {
            "name": "E-commerce Product Page",
            "description": "Product detail page with images, pricing, and actions",
            "skeleton": (
                "A {style} e-commerce product page UI mockup. "
                "Large product image gallery on the left, "
                "product details on the right including: title, price, "
                "star rating, size/color selectors, Add to Cart button, "
                "and product description tabs. {color_context}."
            ),
            "placeholders": {
                "style": "clean, modern",
                "color_context": "White background with accent color for CTA buttons",
            },
            "aspect_ratio": "16:9",
            "resolution": "1K",
            "recommended_model": "gemini",
        },
        "mobile-app": {
            "name": "Mobile App Screen",
            "description": "Mobile application screen mockup",
            "skeleton": (
                "A {style} mobile app screen UI mockup, phone frame aspect ratio. "
                "{screen_description}. "
                "Bottom navigation bar with {nav_items}. "
                "{color_context}. iOS/Android native feel."
            ),
            "placeholders": {
                "style": "modern iOS-style",
                "screen_description": "Home screen with a greeting, search bar, horizontal card scroll, and a vertical feed list",
                "nav_items": "Home, Search, Add, Notifications, Profile icons",
                "color_context": "Light theme with a vibrant accent color",
            },
            "aspect_ratio": "9:16",
            "resolution": "1K",
            "recommended_model": "gemini",
        },
    },
    "game-assets": {
        "character-sprite": {
            "name": "Character Sprite",
            "description": "Game character sprite or concept art",
            "skeleton": (
                "A {style} game character design. "
                "{character_description}. "
                "Full body view, {pose}. "
                "{background}. Sharp details, suitable for game asset."
            ),
            "placeholders": {
                "style": "pixel art 32x32",
                "character_description": "A warrior character wearing plate armor with a glowing sword",
                "pose": "standing in an idle pose facing right",
                "background": "Transparent/flat color background for sprite extraction",
            },
            "aspect_ratio": "1:1",
            "resolution": "1K",
            "recommended_model": "gemini",
        },
        "environment-texture": {
            "name": "Environment Texture",
            "description": "Tileable game environment texture",
            "skeleton": (
                "A seamless tileable {style} texture of {surface}. "
                "Top-down view, consistent lighting, "
                "suitable for game environment floor/wall. "
                "{details}. Uniform edges for tiling."
            ),
            "placeholders": {
                "style": "hand-painted fantasy",
                "surface": "cobblestone road with moss growing between the stones",
                "details": "Warm lighting, subtle wear marks, natural color variation",
            },
            "aspect_ratio": "1:1",
            "resolution": "1K",
            "recommended_model": "imagen",
        },
        "item-icon": {
            "name": "Item Icon",
            "description": "Game item or inventory icon",
            "skeleton": (
                "A {style} game item icon of {item}. "
                "Centered on a {background}. "
                "Clean edges, {detail_level}. "
                "Suitable for game inventory UI."
            ),
            "placeholders": {
                "style": "stylized fantasy",
                "item": "a glowing health potion in a red glass bottle",
                "background": "dark gradient background",
                "detail_level": "detailed with subtle glow effects and highlights",
            },
            "aspect_ratio": "1:1",
            "resolution": "1K",
            "recommended_model": "gemini",
        },
        "background-scene": {
            "name": "Background Scene",
            "description": "Game background or environment scene",
            "skeleton": (
                "A {style} game background scene of {scene}. "
                "{composition}. {atmosphere}. "
                "Wide panoramic view suitable for side-scrolling or menu background."
            ),
            "placeholders": {
                "style": "painted fantasy",
                "scene": "an enchanted forest with ancient trees and glowing mushrooms",
                "composition": "Layered depth with foreground silhouettes, midground details, and a distant horizon",
                "atmosphere": "Soft volumetric lighting filtering through the canopy, mystical atmosphere",
            },
            "aspect_ratio": "16:9",
            "resolution": "2K",
            "recommended_model": "imagen",
        },
        "ui-element": {
            "name": "Game UI Element",
            "description": "Game interface element (button, frame, panel)",
            "skeleton": (
                "A {style} game UI element: {element}. "
                "{details}. "
                "Clean edges on a transparent or flat background. "
                "Suitable for game interface overlay."
            ),
            "placeholders": {
                "style": "medieval fantasy",
                "element": "a decorative frame border for a dialog box with ornate corners",
                "details": "Gold metallic finish with subtle engravings, semi-transparent center area",
            },
            "aspect_ratio": "16:9",
            "resolution": "1K",
            "recommended_model": "gemini",
        },
    },
    "landing-pages": {
        "hero-section": {
            "name": "Hero Section",
            "description": "Landing page hero area with headline and CTA",
            "skeleton": (
                "A {style} landing page hero section mockup. "
                "Large bold headline text, supporting subheadline, "
                "prominent CTA button. {visual_element}. "
                "{color_context}. Above-the-fold design."
            ),
            "placeholders": {
                "style": "modern, high-converting",
                "visual_element": "Abstract 3D illustration on the right side showing the product concept",
                "color_context": "Gradient background from dark blue to purple with white text",
            },
            "aspect_ratio": "16:9",
            "resolution": "2K",
            "recommended_model": "imagen",
        },
        "feature-showcase": {
            "name": "Feature Showcase",
            "description": "Feature grid or list section",
            "skeleton": (
                "A {style} feature showcase section mockup. "
                "Section heading centered at top. "
                "{layout} showing {features}. "
                "Each feature has an icon, title, and short description. "
                "{color_context}."
            ),
            "placeholders": {
                "style": "clean, minimal",
                "layout": "3-column grid",
                "features": "6 product features with unique icons for each",
                "color_context": "White background with subtle shadows on feature cards",
            },
            "aspect_ratio": "16:9",
            "resolution": "1K",
            "recommended_model": "gemini",
        },
        "pricing-table": {
            "name": "Pricing Table",
            "description": "Pricing comparison section with tiers",
            "skeleton": (
                "A {style} pricing table section mockup. "
                "{tiers}. "
                "The recommended tier is visually highlighted and elevated. "
                "Each tier shows: price, feature list with checkmarks, CTA button. "
                "{color_context}."
            ),
            "placeholders": {
                "style": "modern SaaS",
                "tiers": "3 pricing tiers: Starter, Professional (highlighted), Enterprise",
                "color_context": "Clean background, highlighted tier uses brand accent color",
            },
            "aspect_ratio": "16:9",
            "resolution": "1K",
            "recommended_model": "gemini",
        },
        "cta-section": {
            "name": "CTA Section",
            "description": "Call-to-action banner section",
            "skeleton": (
                "A {style} call-to-action section mockup. "
                "Bold heading, supporting text, and a large CTA button. "
                "{visual_treatment}. "
                "Designed to drive conversions at the bottom of a landing page."
            ),
            "placeholders": {
                "style": "vibrant, attention-grabbing",
                "visual_treatment": "Gradient background with subtle pattern overlay, white text, contrasting button color",
            },
            "aspect_ratio": "16:9",
            "resolution": "1K",
            "recommended_model": "gemini",
        },
        "testimonial-area": {
            "name": "Testimonial Section",
            "description": "Social proof section with quotes and avatars",
            "skeleton": (
                "A {style} testimonial section mockup. "
                "{layout} of customer testimonials. "
                "Each testimonial includes a quote, customer photo, name, and title. "
                "Star ratings visible. {color_context}."
            ),
            "placeholders": {
                "style": "trustworthy, professional",
                "layout": "Horizontal carousel with 3 visible cards",
                "color_context": "Light background with quote marks as decorative elements",
            },
            "aspect_ratio": "16:9",
            "resolution": "1K",
            "recommended_model": "gemini",
        },
    },
    "web-components": {
        "navigation-bar": {
            "name": "Navigation Bar",
            "description": "Website or app navigation header",
            "skeleton": (
                "A {style} website navigation bar mockup. "
                "Logo on the left, {nav_items} in the center or right, "
                "{actions}. {color_context}. "
                "Full-width, fixed-header design."
            ),
            "placeholders": {
                "style": "modern, minimal",
                "nav_items": "navigation links: Home, Features, Pricing, Docs, Blog",
                "actions": "Search icon and Sign In / Get Started buttons on the right",
                "color_context": "Dark background with white text, accent-colored CTA button",
            },
            "aspect_ratio": "16:9",
            "resolution": "1K",
            "recommended_model": "gemini",
        },
        "card-component": {
            "name": "Card Component",
            "description": "Reusable card UI element",
            "skeleton": (
                "A {style} UI card component mockup. "
                "{card_content}. "
                "Rounded corners, {shadow}. "
                "{color_context}. "
                "Designed as a reusable component."
            ),
            "placeholders": {
                "style": "modern, clean",
                "card_content": "Header image, title, description text, tags/badges, and action buttons at bottom",
                "shadow": "subtle drop shadow for elevation",
                "color_context": "White card on light gray background",
            },
            "aspect_ratio": "3:4",
            "resolution": "1K",
            "recommended_model": "gemini",
        },
        "modal-dialog": {
            "name": "Modal Dialog",
            "description": "Modal/dialog overlay component",
            "skeleton": (
                "A {style} modal dialog UI mockup. "
                "Centered on a dimmed background overlay. "
                "{modal_content}. "
                "Close button in top-right corner. "
                "{color_context}."
            ),
            "placeholders": {
                "style": "clean, focused",
                "modal_content": "Title, description text, form fields, and primary/secondary action buttons at bottom",
                "color_context": "White modal with rounded corners, dark semi-transparent backdrop",
            },
            "aspect_ratio": "16:9",
            "resolution": "1K",
            "recommended_model": "gemini",
        },
        "data-table": {
            "name": "Data Table",
            "description": "Data table with sorting, filtering, pagination",
            "skeleton": (
                "A {style} data table UI mockup. "
                "Table header with column names and sort indicators. "
                "{table_features}. "
                "Alternating row colors for readability. "
                "{color_context}."
            ),
            "placeholders": {
                "style": "professional, data-dense",
                "table_features": "Search/filter bar above, checkbox selection column, action buttons per row, pagination controls at bottom",
                "color_context": "Clean white background with subtle grid lines and hover highlight",
            },
            "aspect_ratio": "16:9",
            "resolution": "1K",
            "recommended_model": "gemini",
        },
        "form-layout": {
            "name": "Form Layout",
            "description": "Multi-section form with validation",
            "skeleton": (
                "A {style} form layout UI mockup. "
                "{form_sections}. "
                "Labels above inputs, {validation_style}. "
                "Submit and Cancel buttons at bottom. "
                "{color_context}."
            ),
            "placeholders": {
                "style": "clean, user-friendly",
                "form_sections": "Grouped sections with section headings: Personal Info, Contact Details, Preferences",
                "validation_style": "inline validation with green checkmarks for valid fields and red error messages",
                "color_context": "White form on light background with focused input highlighting",
            },
            "aspect_ratio": "16:9",
            "resolution": "1K",
            "recommended_model": "gemini",
        },
    },
    "icons": {
        "app-icon": {
            "name": "App Icon",
            "description": "Application icon for mobile or desktop",
            "skeleton": (
                "A {style} app icon design. "
                "{icon_description}. "
                "Rounded square shape (superellipse), "
                "{color_context}. "
                "Recognizable at small sizes, bold and simple."
            ),
            "placeholders": {
                "style": "modern, flat design",
                "icon_description": "A stylized letter or abstract symbol representing the app concept",
                "color_context": "Vibrant gradient background with white icon symbol",
            },
            "aspect_ratio": "1:1",
            "resolution": "1K",
            "recommended_model": "imagen",
        },
        "feature-icon-set": {
            "name": "Feature Icon Set",
            "description": "Set of consistent feature/menu icons",
            "skeleton": (
                "A set of {count} {style} feature icons arranged in a grid. "
                "Icons for: {icon_list}. "
                "All icons share the same {consistency}. "
                "{color_context}."
            ),
            "placeholders": {
                "count": "6",
                "style": "outlined, minimal",
                "icon_list": "settings, user, search, notifications, analytics, security",
                "consistency": "line weight, corner radius, and visual style",
                "color_context": "Single accent color on a white background, consistent 24px visual size",
            },
            "aspect_ratio": "16:9",
            "resolution": "1K",
            "recommended_model": "gemini",
        },
        "illustration": {
            "name": "Illustration",
            "description": "Custom illustration for UI or marketing",
            "skeleton": (
                "A {style} illustration depicting {subject}. "
                "{composition}. "
                "{color_context}. "
                "Clean vector look suitable for web/app UI."
            ),
            "placeholders": {
                "style": "modern flat illustration",
                "subject": "a person working at a desk with floating UI elements around them",
                "composition": "Centered subject with decorative elements around, balanced layout",
                "color_context": "Limited color palette with soft gradients, complementary accent colors",
            },
            "aspect_ratio": "1:1",
            "resolution": "1K",
            "recommended_model": "imagen",
        },
        "pattern-texture": {
            "name": "Pattern / Texture",
            "description": "Repeating pattern or texture for backgrounds",
            "skeleton": (
                "A seamless repeating {style} pattern of {elements}. "
                "Tileable design with consistent spacing. "
                "{color_context}. "
                "Suitable for website or app background."
            ),
            "placeholders": {
                "style": "geometric, minimal",
                "elements": "abstract shapes and lines forming a subtle repeating grid",
                "color_context": "Monochromatic with subtle opacity variations, very low contrast",
            },
            "aspect_ratio": "1:1",
            "resolution": "1K",
            "recommended_model": "imagen",
        },
        "logo-concept": {
            "name": "Logo Concept",
            "description": "Logo design concept exploration",
            "skeleton": (
                "A {style} logo design concept for {brand}. "
                "{logo_type}. "
                "{color_context}. "
                "Clean, professional, scalable to small sizes."
            ),
            "placeholders": {
                "style": "modern, versatile",
                "brand": "a tech startup focused on AI tools",
                "logo_type": "Abstract mark with integrated typography, geometric forms",
                "color_context": "Two-color design that works on both light and dark backgrounds",
            },
            "aspect_ratio": "1:1",
            "resolution": "1K",
            "recommended_model": "imagen",
        },
    },
}


def get_templates(category: str = "all") -> list[dict]:
    """Get available prompt templates, optionally filtered by category.

    Returns list of dicts with: category, name, description, placeholders, aspect_ratio, model
    """
    results = []
    categories = TEMPLATES.keys() if category == "all" else [category]

    for cat in categories:
        if cat not in TEMPLATES:
            continue
        for key, template in TEMPLATES[cat].items():
            results.append(
                {
                    "category": cat,
                    "key": key,
                    "name": template["name"],
                    "description": template["description"],
                    "placeholders": template["placeholders"],
                    "aspect_ratio": template["aspect_ratio"],
                    "resolution": template.get("resolution", "1K"),
                    "recommended_model": template.get("recommended_model", "gemini"),
                }
            )

    return results


def apply_template(
    category: str,
    template_key: str,
    overrides: Optional[dict] = None,
) -> tuple[str, dict]:
    """Fill a template with user-provided values (or defaults).

    Args:
        category: Template category (e.g., "ui-mockups")
        template_key: Template key (e.g., "dashboard")
        overrides: Dict of placeholder overrides from the user

    Returns:
        Tuple of (filled prompt, template metadata dict)
    """
    if category not in TEMPLATES:
        raise ValueError(f"Unknown template category: {category}. Available: {list(TEMPLATES.keys())}")

    if template_key not in TEMPLATES[category]:
        available = list(TEMPLATES[category].keys())
        raise ValueError(f"Unknown template: {template_key}. Available in {category}: {available}")

    template = TEMPLATES[category][template_key]
    placeholders = dict(template["placeholders"])

    if overrides:
        placeholders.update(overrides)

    prompt = template["skeleton"].format(**placeholders)

    metadata = {
        "template": f"{category}/{template_key}",
        "aspect_ratio": template["aspect_ratio"],
        "resolution": template.get("resolution", "1K"),
        "recommended_model": template.get("recommended_model", "gemini"),
    }

    return prompt, metadata


def enhance(
    prompt: str,
    profile: Optional[dict] = None,
    template: Optional[str] = None,
) -> tuple[str, list[PromptValidationWarning]]:
    """Full prompt enhancement pipeline.

    1. Validate (may raise PromptValidationError)
    2. Apply template if specified
    3. Enrich with style profile context
    4. Structure with scene description format

    Args:
        prompt: Raw user prompt
        profile: Style profile dict (from style_profile.load_profile)
        template: Optional "category/key" template identifier

    Returns:
        Tuple of (enhanced prompt, list of warnings)
    """
    # Step 1: Validate
    warnings = validate(prompt)

    # Step 2: Apply template if specified
    template_meta = {}
    if template and "/" in template:
        category, key = template.split("/", 1)
        try:
            # Use prompt as override for the main content
            template_prompt, template_meta = apply_template(
                category, key, {"content": prompt, "subject": prompt}
            )
            # Blend: template structure + user's specific request
            prompt = f"{template_prompt}\n\nSpecific requirements: {prompt}"
        except ValueError as e:
            warnings.append(
                PromptValidationWarning(
                    f"Template error: {e}",
                    "Proceeding without template. The prompt will still be enhanced.",
                )
            )

    # Step 3: Enrich with style profile
    if profile:
        from .style_profile import apply_to_prompt

        prompt = apply_to_prompt(profile, prompt)

    # Step 4: Add structural hints if the prompt seems bare
    prompt = _add_structural_hints(prompt)

    return prompt, warnings


def _add_structural_hints(prompt: str) -> str:
    """Add composition and technical hints to underdeveloped prompts."""
    lower = prompt.lower()

    hints = []

    # If no lighting mentioned, add a default
    lighting_terms = ["lighting", "lit", "light", "shadow", "glow", "bright", "dark", "ambient"]
    if not any(term in lower for term in lighting_terms):
        hints.append("Professional, even lighting")

    # If no composition mentioned for UI mockups
    ui_terms = ["mockup", "ui", "interface", "dashboard", "page", "screen", "app"]
    composition_terms = ["layout", "composition", "arranged", "grid", "centered", "aligned"]
    if any(term in lower for term in ui_terms) and not any(
        term in lower for term in composition_terms
    ):
        hints.append("Clean, organized layout with clear visual hierarchy")

    # If no resolution/quality hint
    quality_terms = ["high quality", "detailed", "sharp", "crisp", "professional", "polished"]
    if not any(term in lower for term in quality_terms):
        hints.append("High quality, detailed rendering")

    if hints:
        hints_str = ". ".join(hints)
        return f"{prompt}\n\n{hints_str}."

    return prompt
