# Project-Type Specific Guidance

## Game Projects

### Art Styles
- **Pixel Art**: Specify exact resolution (16x16, 32x32, 64x64). Mention "limited color palette" for retro authenticity. Add "clean pixel edges, no anti-aliasing" for true pixel art.
- **Isometric**: "45-degree isometric perspective, consistent vanishing point". Good for strategy/management games.
- **Hand-Painted**: "Hand-painted texture style, visible brush strokes, painterly". Good for RPG/adventure games.
- **3D Rendered**: "3D rendered, PBR materials, realistic lighting". For 3D game assets.
- **Flat/Vector**: "Flat vector style, bold colors, clean shapes". For casual/mobile games.

### Asset Considerations
- **Sprites**: Always request "transparent or flat color background for sprite extraction"
- **Tileables**: Add "seamless tileable, uniform edges" for textures that need to repeat
- **UI Elements**: Request "clean edges, semi-transparent where needed" for overlay elements
- **Icons**: Specify "consistent size, centered, matching style across set"

### Color Palettes
- Retro/NES: 4-color palette per sprite, limited to 54 total colors
- SNES/16-bit: Richer palettes, but still limited per sprite
- Modern pixel: Full color range, pixel art style without hardware constraints
- Use the style profile to lock in a palette

## Landing Pages

### Above-the-Fold Focus
- Hero images: Use 16:9, emphasize visual impact and brand messaging
- Keep text areas clear for headline overlay
- Include visual hierarchy: hero image > headline > subheadline > CTA

### Section Types
- **Hero**: Bold, attention-grabbing, single focal point
- **Features**: Grid layout with icons, balanced spacing
- **Pricing**: Clear tier comparison, highlighted recommended option
- **Testimonials**: Trust signals, real-looking (but AI-generated) avatars
- **CTA**: High contrast, urgency-creating, clear action

### Conversion Design
- CTA buttons should be the most prominent colored element
- Visual flow should guide the eye: top-left → center → CTA button
- White space is intentional — don't fill every pixel
- Trust signals (logos, ratings, security badges) near conversion points

### Mobile Responsiveness
- Generate both desktop (16:9) and mobile (9:16) versions
- Mobile: stack elements vertically, larger touch targets
- Consider how the design will reflow

## Web Applications

### Component-Level Design
- Generate individual components, not entire page compositions
- Each component should be self-contained with clear boundaries
- Include hover/active states in the description when relevant

### Design System Adherence
- Reference the design system in every prompt (Material, Ant, custom)
- Consistent spacing: "8px grid system" or "4px base unit"
- Consistent border radius: "4px rounded corners throughout"
- Consistent shadow scale: "subtle shadow for cards, stronger for modals"

### Dark/Light Mode
- Generate variants: "Dark mode version with..." then "Light mode version with..."
- Ensure sufficient contrast in both modes
- Use the style profile to switch between dark and light palettes

### Data-Heavy Layouts
- Tables: "Alternating row colors, clear header row, action column"
- Charts: Specify type (line, bar, pie, area) and data representation
- Forms: "Labels above inputs, inline validation, clear required indicators"
- Dashboards: "Information hierarchy: summary → charts → detailed data"

### Common Patterns
- **Navigation**: Sidebar (app) vs top bar (marketing) vs bottom bar (mobile)
- **Cards**: Consistent padding, border radius, shadow, hover effect
- **Modals**: Centered, dimmed backdrop, clear close action, focused content
- **Empty States**: Illustration + message + primary action button
- **Loading States**: Skeleton screens matching the content layout
