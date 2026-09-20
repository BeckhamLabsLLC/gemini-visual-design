---
expect:
  image_path: string
---
{
  "overall_score": 6,
  "summary": "Clear structure, but the primary action is hard to find and body copy sits below comfortable reading contrast.",
  "categories": { "color": 5, "layout": 7, "typography": 6, "hierarchy": 5 },
  "issues": [
    {
      "severity": "high",
      "category": "hierarchy",
      "description": "The primary call to action has the same visual weight as two secondary buttons, so nothing draws the eye.",
      "edit_instruction": "Make the primary button solid #7c3aed with white text, and render the two secondary buttons as outline-only with a 1px #334155 border."
    },
    {
      "severity": "medium",
      "category": "color",
      "description": "Body text at #64748b on #0b1020 is roughly 3.4:1, below the 4.5:1 needed for normal text.",
      "edit_instruction": "Lighten body text to #cbd5e1 while leaving headings and the background unchanged."
    }
  ],
  "strengths": ["Consistent 8px spacing rhythm", "Restrained palette"],
  "image_path": "{{input.image_path}}",
  "focus": "overall",
  "project_type": "web-app"
}
