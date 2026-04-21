---
name: create-video
description: Generate short video clips from text or reference images
argument-hint: "[description of the video to generate]"
allowed-tools:
  - Read
  - Glob
  - Grep
  - mcp__gemini-visual-design__generate_video
  - mcp__gemini-visual-design__save_asset
  - mcp__gemini-visual-design__list_generated
  - mcp__gemini-visual-design__get_prompt_templates
---

# Create Video Command

Generate short video clips using Google Veo models.

## Instructions

Follow this workflow strictly:

### 1. Understand the Request
- If an argument is provided, use it as the video description
- If no argument, ask what kind of video to generate
- Clarify: motion style, camera movement, duration, mood

### 2. Choose Model
- **veo-3.1-fast** (default): Faster iteration — good for most use cases
- **veo-3.1**: Best quality — use for premium or complex scenes

Ask the user which model to use if they haven't specified.

### 3. Craft the Prompt
- Focus on **motion**: describe what moves, how it moves, camera motion
- Include: subject, action, environment, lighting, mood, camera angle
- Example: "Slow dolly forward through a misty forest at dawn, soft volumetric light filtering through the canopy, gentle camera shake"
- Use `get_prompt_templates` for inspiration if needed

### 4. Generate
- Call `generate_video` with the prompt and chosen model
- Warn the user: video generation takes 1-3 minutes
- If a reference image is available, pass it as `reference_image` for image-to-video

### 5. Review and Save
- Show the user the video path so they can preview it
- Report the enhanced prompt and any warnings
- If satisfied, use `save_asset` to save to the project directory
- If not, adjust the prompt and regenerate

## Output Format

After generation, report:
- Video file path (so user can view it)
- Model used
- Enhanced prompt
- Any warnings
- Suggested next action (save, regenerate with adjustments, or try a different model)
