#!/usr/bin/env python3
"""PreToolUse guard: block writes that would commit a secret to disk.

Reads the hook payload on stdin. Exit 2 blocks the tool call and hands stderr
back to Claude as feedback, so the model sees why and can correct itself.
Any other exit code lets the call through: this guard never breaks a session
because of its own bugs.

Projects can allow specific strings in `.claude/secret-guard-allow`, one
regular expression per line.
"""
import json
import os
import re
import sys
from pathlib import Path

# Paths that should never be written by an agent.
BLOCKED_PATHS = re.compile(
    r"(^|/)("
    r"\.env(\.[\w.-]+)?"
    r"|\.npmrc|\.pypirc|\.netrc"
    r"|id_rsa|id_dsa|id_ecdsa|id_ed25519"
    r"|credentials|\.aws/credentials|\.ssh/config"
    r"|secrets?\.ya?ml|secrets?\.json"
    r"|application-(prod|production|prd)\.(ya?ml|properties)"
    r"|service-account.*\.json|gcp-key.*\.json"
    r")$"
    r"|\.(pem|p12|pfx|jks|keystore)$"
)

# Literal secrets. Each pattern is specific enough that a match is a real
# finding, not a variable named "token".
SECRETS = [
    ("AWS access key id", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("AWS secret access key", re.compile(
        r"aws_secret_access_key\s*[=:]\s*[\"']?[A-Za-z0-9/+=]{40}")),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI API key", re.compile(r"\bsk-(proj-)?[A-Za-z0-9]{32,}")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}")),
    ("Stripe live key", re.compile(r"\b[sr]k_live_[A-Za-z0-9]{16,}")),
    ("Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("npm token", re.compile(r"\bnpm_[A-Za-z0-9]{36}\b")),
    ("PyPI token", re.compile(r"\bpypi-AgEIcHlwaS5vcmc[A-Za-z0-9_-]{20,}")),
    ("SendGrid key", re.compile(r"\bSG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}\b")),
    ("Twilio key", re.compile(r"\bSK[0-9a-fA-F]{32}\b")),
    ("private key block", re.compile(
        r"-----BEGIN (RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY-----")),
    ("GCP service account key", re.compile(
        r"\"type\"\s*:\s*\"service_account\"|\"private_key_id\"\s*:\s*\"[0-9a-f]{40}\"")),
    ("Azure storage key", re.compile(
        r"AccountKey\s*=\s*[A-Za-z0-9/+=]{60,}", re.I)),
    ("Azure AD client secret", re.compile(
        r"client_secret\s*[=:]\s*[\"']?[A-Za-z0-9~._-]{34,}")),
    ("signed JWT", re.compile(
        r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{20,}")),
    ("Basic auth header", re.compile(
        r"Authorization[\"']?\s*:\s*[\"']?\s*Basic\s+[A-Za-z0-9+/]{20,}={0,2}", re.I)),
    ("Bearer token", re.compile(
        r"Authorization[\"']?\s*:\s*[\"']?\s*Bearer\s+[A-Za-z0-9._~+/-]{30,}", re.I)),
    ("JDBC url with password", re.compile(
        r"jdbc:[\w:]+//[^\s\"']*[?&;]password=[^\s\"'&;]+", re.I)),
    ("connection string with password", re.compile(
        r"://[^\s:/\"']+:[^\s@\"']{6,}@[\w.-]+", re.I)),
]

# Written by a human on purpose, or obviously not a real value.
#
# The word markers are deliberately case-sensitive. Lowercase "example" appears
# inside the reserved documentation domains — example.com, example.net — and
# matching it would let a real password through in
# `mongodb://admin:hunter2@cluster0.example.net`. Placeholder conventions are
# uppercase in practice, including AWS's own AKIAIOSFODNN7EXAMPLE.
ALLOW = re.compile(
    r"(EXAMPLE|PLACEHOLDER|REDACTED|CHANGEME|DUMMY|FAKE|SAMPLE|YOUR_[A-Z_]+"
    r"|<[^>]+>|\$\{[^}]+\}|\$[A-Z_]{3,}|\.\.\.|[xX]{5,})"
)

# Shell redirections and common writers, so `cat > .env` is caught the same
# way a Write to .env is.
REDIRECT = re.compile(r">>?\s*([^\s;&|>]+)")
WRITERS = re.compile(
    r"\b(?:tee|install)\s+(?:-\S+\s+)*([^\s;&|]+)"
    r"|\bcp\s+(?:-\S+\s+)*\S+\s+([^\s;&|]+)"
    r"|\bmv\s+(?:-\S+\s+)*\S+\s+([^\s;&|]+)"
)


def project_allowlist():
    """Regexes this project has explicitly allowed, if any."""
    root = os.environ.get("CLAUDE_PROJECT_DIR")
    if not root:
        return []
    path = Path(root) / ".claude" / "secret-guard-allow"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []

    allowed = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            allowed.append(re.compile(line))
        except re.error:
            continue  # a broken line must not disable the guard
    return allowed


def text_of(tool_input):
    """Everything this call would write, as one string."""
    parts = []
    for key in ("content", "new_string", "command"):
        value = tool_input.get(key)
        if isinstance(value, str):
            parts.append(value)
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        for edit in edits:
            if isinstance(edit, dict) and isinstance(edit.get("new_string"), str):
                parts.append(edit["new_string"])
    return "\n".join(parts)


def written_paths(tool_input):
    """Every path this call would write to."""
    paths = []
    for key in ("file_path", "notebook_path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            paths.append(value)

    command = tool_input.get("command")
    if isinstance(command, str):
        for match in REDIRECT.finditer(command):
            paths.append(match.group(1))
        for match in WRITERS.finditer(command):
            paths.extend(group for group in match.groups() if group)
    return paths


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0

    for path in written_paths(tool_input):
        if BLOCKED_PATHS.search(path.strip("\"'")):
            print(
                f"Blocked: {path} holds credentials and must not be written by "
                f"an agent.\n"
                "Put the value in your secret manager and reference it from "
                "config, or ask the user to edit this file themselves.",
                file=sys.stderr,
            )
            return 2

    body = text_of(tool_input)
    if not body:
        return 0

    allowlist = project_allowlist()

    for label, pattern in SECRETS:
        for match in pattern.finditer(body):
            snippet = match.group(0)
            if ALLOW.search(snippet):
                continue
            if any(rule.search(snippet) for rule in allowlist):
                continue
            line = body[: match.start()].count("\n") + 1
            masked = snippet[:6] + "…" + snippet[-2:] if len(snippet) > 12 else "…"
            print(
                f"Blocked: this writes what looks like a real {label} "
                f"(line {line} of the new content, {masked}).\n"
                "Replace it with an environment variable or a secret-manager "
                "lookup. If the value is fake, make that obvious — use EXAMPLE "
                "or a ${PLACEHOLDER} — and try again.\n"
                "If this project legitimately needs the string, add a regex "
                "for it to .claude/secret-guard-allow.",
                file=sys.stderr,
            )
            return 2

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # A broken guard must not block the session.
        sys.exit(0)
