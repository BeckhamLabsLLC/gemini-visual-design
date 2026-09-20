# Security Policy

## Reporting a vulnerability

Please report security issues privately through
[GitHub Security Advisories](https://github.com/BeckhamLabsLLC/gemini-visual-design/security/advisories/new)
rather than opening a public issue.

## What this plugin does with your data

- **Your prompts and images go to Google.** Every prompt, and every image
  passed to `edit_image` or `analyze_design`, is uploaded to the Gemini API.
  Your `.gemini-design-profile.json` contents (colors, fonts, framework) are
  injected into prompts and sent too.
- **One outbound host.** `generativelanguage.googleapis.com`, via the
  `google-genai` SDK. There is no telemetry, no analytics, and no
  first-party backend.
- **Your API key** is read from the `GEMINI_API_KEY` environment variable.
  It is never logged — the startup line records only `[set]` or `[missing]`.
- **Local files.** Generated assets and metadata sidecars are written to
  `~/.cache/gemini-visual-design/preview/` and pruned after 7 days.
  `save_asset` copies into a directory you name; the destination is
  constrained to your project root and the filename must be a bare filename
  with no path separators.

## Scope

The plugin executes no user-supplied code and spawns no subprocesses. The
main risk surface is filesystem writes via `save_asset` and
`init_style_profile`, and prompt content reaching a third party.
