#!/usr/bin/env bash
set -euo pipefail
cat > CLAUDE.md <<'MD'
# Project

IMPORTANT: ALWAYS write clean code and handle errors properly.
CRITICAL: You MUST follow best practices. This is MANDATORY.
IMPORTANT: NEVER write bad tests. ALWAYS be careful. This is REQUIRED.
IMPORTANT: ALWAYS use appropriate logging. CRITICAL.

Don't use field injection.

Avoid deep nesting.

@docs/architecture.md
MD
