#!/usr/bin/env bash
# SessionStart hook: warn if GEMINI_API_KEY is not set.
# Non-blocking — always continues, but adds a system message warning.

if [ -z "${GEMINI_API_KEY:-}" ]; then
  cat <<'EOF'
{
  "continue": true,
  "systemMessage": "GEMINI_API_KEY is not set. Visual design tools will fail until you set it.\n\nRun: export GEMINI_API_KEY=\"your-key\"\nGet a key at: https://aistudio.google.com/apikey"
}
EOF
else
  echo '{"continue": true}'
fi
