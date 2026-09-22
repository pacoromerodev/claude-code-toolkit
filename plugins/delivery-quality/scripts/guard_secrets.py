#!/usr/bin/env python3
"""PreToolUse guard: block writes that would commit a secret to disk.

Reads the hook payload on stdin. Exit 2 blocks the tool call and hands stderr
back to Claude as feedback, so the model sees why and can correct itself.
Any other exit code lets the call through: this guard never breaks a session
because of its own bugs.

Two checks:

  - the paths a call writes — Write, Edit and NotebookEdit targets, and in a
    shell command the targets of redirects, tee, cp, mv and install — against
    files that hold credentials
  - the content a call writes against patterns specific enough that a match is
    a real key. A shell command that only searches or reads (grep, rg,
    git log -S, cat …) and writes no file is not scanned: looking for a leaked
    key is not leaking it

Projects can allow specific strings in `.claude/secret-guard-allow`, one
regular expression per line. That file, like its sibling for the destructive
guard, is itself blocked: an exception is the user's decision, not the agent's.
"""
import json
import os
import re
import shlex
import sys
from pathlib import Path

SHELL_TOOLS = {"Bash", "PowerShell"}

# Paths that should never be written by an agent. `/` or `\` before the name,
# so Windows paths are covered too. `.env.example` and its siblings are
# templates meant to be committed; their content is still scanned.
BLOCKED_PATHS = re.compile(
    r"(^|[/\\])("
    r"\.env(\.(?!(example|sample|template|dist|defaults)$)[\w.-]+)?"
    r"|\.npmrc|\.pypirc|\.netrc"
    r"|id_rsa|id_dsa|id_ecdsa|id_ed25519"
    r"|credentials|\.aws[/\\]credentials|\.ssh[/\\]config"
    r"|secrets?\.ya?ml|secrets?\.json"
    r"|application-(prod|production|prd)\.(ya?ml|properties)"
    r"|service-account.*\.json|gcp-key.*\.json"
    r")$"
    r"|\.(pem|p12|pfx|jks|keystore)$"
)

# The guards' own exception lists. The agent is the party they constrain.
GUARD_FILES = re.compile(r"(^|[/\\])\.claude[/\\](secret|destructive)-guard-allow$")

# Literal secrets. Each pattern is specific enough that a match is a real
# finding, not a variable named "token".
SECRETS = [
    ("AWS access key id", re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("AWS secret access key", re.compile(
        r"aws_secret_access_key\s*[=:]\s*[\"']?[A-Za-z0-9/+=]{40}")),
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI API key", re.compile(r"\bsk-(proj-)?[A-Za-z0-9]{32,}")),
    ("GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{60,}")),
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
    # The password part stops at a slash, so a host with a port followed by a
    # path containing an at-sign (an API route such as /users/@me) is not read
    # as a credential.
    ("connection string with password", re.compile(
        r"://[^\s:/\"']+:[^\s@\"'/]{6,}@[\w.-]+", re.I)),
]

# Written by a human on purpose, or obviously not a real value.
#
# The word markers are deliberately case-sensitive. Lowercase "example" appears
# inside the reserved documentation domains (example.com, example.net), and
# matching it would let a real password through in a connection string to a
# host under one of them. Placeholder conventions are uppercase in practice,
# including the key AWS uses in its own documentation, which ends in EXAMPLE.
ALLOW = re.compile(
    r"(EXAMPLE|PLACEHOLDER|REDACTED|CHANGEME|DUMMY|FAKE|SAMPLE|YOUR_[A-Z_]+"
    r"|<[^>]+>|\$\{[^}]+\}|\$[A-Z_]{3,}|\.\.\.|[xX]{5,})"
)

# Shell programs that only read or search. A command made only of these, with
# no redirect into a file, writes nothing, so its text is not scanned.
READ_ONLY = {"grep", "egrep", "fgrep", "rg", "ag", "ack", "find", "ls", "cat",
             "head", "tail", "wc", "less", "more", "sort", "uniq", "cut", "echo"}
READ_ONLY_GIT = {"grep", "log", "show", "diff", "blame", "status"}
SEPARATORS = {";", ";;", "&&", "||", "|", "|&", "&", "(", ")"}
WRITE_REDIRECTS = {">", ">>", ">|", "&>", "&>>"}
HARMLESS_TARGETS = {"/dev/null", "/dev/stdout", "/dev/stderr"}


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


def shell_segments(command):
    """[(tokens, [write targets])] for each command in a shell line."""
    try:
        lexer = shlex.shlex(command.replace("\n", " ; "), posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    segments, current, targets, i = [], [], [], 0
    while i < len(tokens):
        token = tokens[i]
        if token in SEPARATORS:
            if current or targets:
                segments.append((current, targets))
            current, targets = [], []
        elif token in WRITE_REDIRECTS:
            if i + 1 < len(tokens):
                targets.append(tokens[i + 1])
                i += 1
        elif token in {"<", "<<", "<<<", ">&", "<&"}:
            i += 1  # an input source or fd duplication, not a file written
        elif token.isdigit() and i + 1 < len(tokens) and tokens[i + 1] in WRITE_REDIRECTS:
            pass  # the fd number in `2>file`
        else:
            current.append(token)
        i += 1
    if current or targets:
        segments.append((current, targets))
    return segments


def shell_writes(command):
    """(paths the command writes, whether it writes anything at all)."""
    paths, writes = [], False
    for tokens, targets in shell_segments(command):
        real = [t for t in targets if t not in HARMLESS_TARGETS and not t.startswith("&")]
        paths.extend(real)
        writes = writes or bool(real)
        if not tokens:
            continue
        program = os.path.basename(tokens[0])
        positional = [t for t in tokens[1:] if not t.startswith("-")]
        if program == "tee":
            paths.extend(positional)
            writes = writes or bool(positional)
        elif program in {"cp", "mv", "install"} and len(positional) >= 2:
            paths.append(positional[-1])
            writes = True
        elif program.lower() in {"out-file", "set-content", "add-content"}:
            writes = True
            if "-Path" in tokens and tokens.index("-Path") + 1 < len(tokens):
                paths.append(tokens[tokens.index("-Path") + 1])
    return paths, writes


def only_reads(command):
    """True when every command in the line is a read or a search."""
    for tokens, _ in shell_segments(command):
        if not tokens:
            continue
        program = os.path.basename(tokens[0])
        if program == "git":
            rest = [t for t in tokens[1:] if not t.startswith("-")]
            if not rest or rest[0] not in READ_ONLY_GIT:
                return False
        elif program not in READ_ONLY:
            return False
    return True


def text_of(tool_name, tool_input):
    """Everything this call would put on disk, as one string."""
    parts = []
    for key in ("content", "new_string", "new_source"):
        value = tool_input.get(key)
        if isinstance(value, str):
            parts.append(value)
    command = tool_input.get("command")
    if isinstance(command, str):
        _, writes = shell_writes(command)
        if writes or tool_name not in SHELL_TOOLS or not only_reads(command):
            parts.append(command)
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
        paths.extend(shell_writes(command)[0])
    return [p.strip("\"'") for p in paths]


def clip(text, limit=200):
    return text if len(text) <= limit else text[:limit - 1] + "…"


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0
    tool_name = payload.get("tool_name") or ""

    for path in written_paths(tool_input):
        if GUARD_FILES.search(path):
            print(
                f"Blocked by guard_secrets: {clip(path)} is a guard's exception "
                "list. Adding an exception is the user's decision.\n"
                "Do not write it another way. If a string really must be "
                "allowed, tell the user which one and why, and ask them to add "
                "it themselves.",
                file=sys.stderr,
            )
            return 2
        if BLOCKED_PATHS.search(path):
            print(
                f"Blocked by guard_secrets: {clip(path)} has the name of a "
                "credential file, and an agent never writes one, whatever the "
                "content. Nothing was written.\n"
                "Do not retry through another tool, a shell redirect, or a copy "
                "or rename. If it is a template with placeholder values, name it "
                "like one (.env.example). If real values are needed, list the "
                "keys the file must contain and let the user fill them in.",
                file=sys.stderr,
            )
            return 2

    body = text_of(tool_name, tool_input)
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
            masked = snippet[:6] + "…" + snippet[-2:] if len(snippet) > 12 else "…"
            if tool_name in SHELL_TOOLS:
                where = "this command line"
                instead = (
                    "- Writing or passing it: don't. Reference an environment "
                    "variable the user has set ($NAME) and ask them to set it "
                    "if it is missing.\n"
                    "- Looking for where it leaked: search for the pattern, "
                    "not the value, e.g. grep -rnE 'AKIA[0-9A-Z]{16}' ."
                )
            else:
                line = body[: match.start()].count("\n") + 1
                where = f"the text you are writing (line {line} of it, not of the file)"
                instead = (
                    "- The code needs it at runtime: read it from an environment "
                    "variable and tell the user which variable to set.\n"
                    "- It is test or sample data: use an obviously fake value "
                    "containing EXAMPLE, or a ${PLACEHOLDER}."
                )
            print(
                f"Blocked by guard_secrets: {where} contains a string shaped "
                f"like a real {label} ({masked}). Nothing was written.\n"
                "Do not retry with the value split, encoded or moved to another "
                "file; that still puts the secret on disk.\n"
                f"{instead}\n"
                "- The user says this exact string must be kept: stop and ask "
                "them to add the exception themselves.",
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
