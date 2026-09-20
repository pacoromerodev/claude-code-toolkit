#!/usr/bin/env bash
set -euo pipefail
mkdir -p .claude
cat > .claude/settings.json <<'JSON'
{
  "permissions": {
    "allow": ["Bash", "Write", "Read(*)"]
  },
  "env": {
    "INTERNAL_API_KEY": "sk-ant-api03-NotARealKeyButShapedLikeOne123456"
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{ "type": "command", "command": "./scripts/format.sh" }]
      }
    ]
  }
}
JSON
