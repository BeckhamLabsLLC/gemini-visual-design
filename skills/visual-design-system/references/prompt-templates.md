# Prompt Templates Reference

Quick-reference for all built-in prompt templates. Use `get_prompt_templates` tool to browse programmatically.

## UI Mockups

### Dashboard
```
A professional [dark-themed/light] dashboard UI mockup. Left sidebar navigation
with icons, top header bar with user avatar and notifications, main content area
with [KPI cards/charts/data tables]. [Color context]. Clean, modern interface.
```

### Settings Page
```
A clean [minimal] settings page UI mockup. Organized into sections:
[Profile, Notifications, Privacy, Appearance]. Each section has a heading
and grouped controls. Toggle switches, dropdowns, and text inputs.
```

### Login / Signup
```
A [modern, polished] login page UI mockup. Split layout with [branded
illustration] on the left and centered auth form on the right. Email field,
password field, social login buttons, 'Forgot password' link.
```

### E-commerce Product
```
A [clean, modern] e-commerce product page UI mockup. Large product image
gallery on the left, product details on the right: title, price, star rating,
size/color selectors, Add to Cart button, description tabs.
```

### Mobile App Screen
```
A [modern iOS-style] mobile app screen mockup, phone frame aspect ratio.
[Screen description]. Bottom navigation bar with [icon list].
[Light/dark] theme with vibrant accent color.
```

## Game Assets

### Character Sprite
```
A [pixel art 32x32] game character design. [Character description].
Full body view, [idle/action pose]. Transparent background for sprite extraction.
```

### Environment Texture
```
A seamless tileable [hand-painted fantasy] texture of [surface description].
Top-down view, consistent lighting, suitable for game environment.
Uniform edges for tiling.
```

### Item Icon
```
A [stylized fantasy] game item icon of [item description].
Centered on a [dark gradient] background. Detailed with subtle glow effects.
Suitable for game inventory UI.
```

### Background Scene
```
A [painted fantasy] game background scene of [scene description].
Layered depth with foreground, midground, and distant horizon.
[Atmosphere description]. Wide panoramic view.
```

## Landing Pages

### Hero Section
```
A [modern, high-converting] landing page hero section mockup. Large bold
headline text, supporting subheadline, prominent CTA button.
[3D illustration/gradient/photo] on the right. [Color context].
```

### Feature Showcase
```
A [clean, minimal] feature showcase section mockup. Section heading centered.
[3-column grid] showing [N] product features with unique icons, titles,
and short descriptions. [Color context].
```

### Pricing Table
```
A [modern SaaS] pricing table section mockup. [3] pricing tiers:
[Starter, Professional (highlighted), Enterprise]. Each shows price,
feature list with checkmarks, CTA button. Highlighted tier elevated.
```

## Web Components

### Navigation Bar
```
A [modern, minimal] website navigation bar mockup. Logo on left,
[nav links] in center, [Search + Sign In + CTA buttons] on right.
Full-width, fixed-header design. [Color context].
```

### Card Component
```
A [modern, clean] UI card component mockup. [Header image, title,
description, tags, action buttons]. Rounded corners, subtle shadow.
Designed as reusable component.
```

### Data Table
```
A [professional] data table UI mockup. Header row with sort indicators.
Search/filter bar, checkbox selection, action buttons per row,
pagination controls. Alternating row colors.
```

## Icons & Assets

### App Icon
```
A [modern, flat design] app icon. [Symbol/letter description].
Rounded square shape (superellipse). [Gradient background with white symbol].
Recognizable at small sizes.
```

### Feature Icon Set
```
A set of [6] [outlined, minimal] feature icons in a grid. Icons for:
[list of concepts]. Same line weight, corner radius, visual style.
Single accent color on white, consistent 24px visual size.
```

### Illustration
```
A [modern flat] illustration of [subject]. [Composition description].
Limited color palette with soft gradients. Clean vector look for web/app UI.
```

## Usage

Pass templates to `generate_image` as `template` parameter:
```
template: "ui-mockups/dashboard"
template: "game-assets/character-sprite"
template: "landing-pages/hero-section"
template: "icons/app-icon"
```

Override default placeholder values in your prompt text — the engine will blend your specifics with the template structure.
