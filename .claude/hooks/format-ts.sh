#!/bin/bash
# Auto-format TypeScript/TSX files after edit

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ "$FILE_PATH" == *.ts || "$FILE_PATH" == *.tsx ]]; then
  if command -v npx &> /dev/null && [ -f "short-gravity-web/package.json" ]; then
    cd short-gravity-web && npx prettier --write "../$FILE_PATH" 2>/dev/null || true
  fi
fi

exit 0
