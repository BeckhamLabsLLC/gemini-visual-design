---
expect:
  project_type: [game, landing-page, web-app, general]
---
{
  "profile_path": "/workspace/.gemini-design-profile.json",
  "project_root": "/workspace",
  "project_root_source": "CLAUDE_PROJECT_DIR",
  "created": true,
  "profile": {
    "project_type": "{{input.project_type}}",
    "colors": {
      "primary": "#7c3aed",
      "secondary": "#06b6d4",
      "background": "#0b1020",
      "surface": "#111827",
      "text": "#e5e7eb"
    },
    "typography": { "heading_font": "Inter", "style": "modern sans-serif" },
    "visual_style": "clean, minimal, dark mode support",
    "framework": "tailwind"
  }
}
