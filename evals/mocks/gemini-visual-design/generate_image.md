---
expect:
  prompt: string
  model: [draft, fast, pro, auto, gemini, imagen, flash, final, lite]
---
{
  "generated": [
    {
      "path": "/home/user/.cache/gemini-visual-design/preview/gen_20260919_120000_a1b2c3d4.png",
      "model": "gemini-3.1-flash-image",
      "tier": "fast",
      "enhanced_prompt": "{{input.prompt}}",
      "warnings": []
    }
  ],
  "preview_dir": "/home/user/.cache/gemini-visual-design/preview",
  "tip": "Use edit_image to refine, or save_asset to save to your project."
}
