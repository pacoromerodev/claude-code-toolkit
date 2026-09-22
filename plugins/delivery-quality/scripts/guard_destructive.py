#!/usr/bin/env python3
"""PreToolUse guard: block commands that destroy work you cannot get back.

The test is not "is this dangerous" — most useful commands are. It is whether
the damage survives the session: a force-push that rewrites shared history, a
reset that discards uncommitted work, a delete outside the project, a DROP
against something that is not a test database.

The command is parsed, not pattern-matched as one string. It is split into the
commands the shell would actually run — on `;`, `&&`, `||`, `|`, `&` and
unquoted newlines — and each is tokenised the way the shell would, so flag
order, quoting and `sudo`/`env` wrappers do not change the verdict. Text that
is only data (a heredoc written to a file, a quoted commit message) is not
mistaken for a command; text that runs (`bash -c`, `$(…)`, a heredoc fed to a
shell) is checked too. SQL is the exception: it always arrives as quoted
data for a database client, so it is read from inside the quotes.

Exit 2 blocks and hands stderr to Claude. Anything else lets the call through,
including every unexpected error: a broken guard must not brick a session.

Projects can relax this in `.claude/destructive-guard-allow`, one regular
expression per line. A rule exempts only the command it matches, not the whole
line it is chained into.
"""
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

PROTECTED_BRANCHES = {"main", "master", "develop", "release", "production"}
MAX_ECHO = 200

SEPARATORS = {";", ";;", "&&", "||", "|", "|&", "&", "(", ")", "{", "}"}
REDIRECTS = {">", ">>", "<", "<<", "<<<", ">&", "<&", "&>", "&>>", ">|", "<>"}
WRAPPERS = {"sudo", "doas", "env", "nohup", "time", "command", "exec", "nice",
            "ionice", "stdbuf", "timeout", "xargs", "builtin"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
DB_CLIENTS = {"psql", "mysql", "mariadb", "sqlite3", "sqlcmd", "clickhouse-client",
              "cockroach", "duckdb", "pgcli", "mycli"}

# A test or local target named in the connection arguments. Letters on either
# side break the match, so "developer" and "latest" do not count, while
# app_test, dev-cluster and localhost do.
TEST_MARKER = re.compile(
    r"(?<![a-z])(test|tests|testing|dev|local|localhost|fixture|fixtures|"
    r"sandbox|staging|tmp|ci|127\.0\.0\.1)(?![a-z])", re.I)

HEREDOC = re.compile(r"(?<!<)<<(-?)\s*(['\"]?)([A-Za-z_][\w.-]*)\2")


def clip(text):
    text = " ".join(str(text).split())
    return text if len(text) <= MAX_ECHO else text[:MAX_ECHO - 1] + "…"


def project_root(payload):
    for candidate in (
        os.environ.get("CLAUDE_PROJECT_DIR"),
        payload.get("cwd"),
        os.getcwd(),
    ):
        if candidate and Path(candidate).is_dir():
            return Path(candidate).resolve()
    return Path.cwd().resolve()


def allowlist(root):
    path = root / ".claude" / "destructive-guard-allow"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    rules = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            try:
                rules.append(re.compile(line))
            except re.error:
                continue
    return rules


def git(root, *args):
    try:
        result = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() if result.returncode == 0 else None
    except Exception:
        return None


# --------------------------------------------------------------------------
# Parsing the command into the commands the shell would run
# --------------------------------------------------------------------------

def split_heredocs(command):
    """(command without heredoc bodies, [(opener line, body)])."""
    lines = command.split("\n")
    kept, bodies, pending = [], [], []
    i = 0
    while i < len(lines):
        line = lines[i]
        if pending:
            strip_tabs, delimiter, opener, body = pending[0]
            candidate = line.lstrip("\t") if strip_tabs else line
            if candidate == delimiter:
                bodies.append((opener, "\n".join(body)))
                pending.pop(0)
            else:
                body.append(line)
            i += 1
            continue
        kept.append(line)
        for match in HEREDOC.finditer(line):
            pending.append((match.group(1) == "-", match.group(3), line, []))
        i += 1
    for _, _, opener, body in pending:  # unterminated: still a body
        bodies.append((opener, "\n".join(body)))
    return "\n".join(kept), bodies


def mask_newlines(command):
    """Unquoted newlines separate commands; turn them into `;`."""
    out, quote, escaped = [], None, False
    for char in command:
        if escaped:
            out.append(char)
            escaped = False
            continue
        if char == "\\" and quote != "'":
            escaped = True
            out.append(char)
            continue
        if quote:
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char == "\n":
            out.append(" ; ")
            continue
        out.append(char)
    return "".join(out)


def substitutions(command):
    """Command substitutions outside single quotes: `$(…)` and backticks."""
    found, i, quote = [], 0, None
    while i < len(command):
        char = command[i]
        if quote == "'":
            if char == "'":
                quote = None
        elif char == "'" and quote is None:
            quote = "'"
        elif char == '"':
            quote = None if quote == '"' else '"'
        elif command.startswith("$(", i):
            depth, j = 1, i + 2
            while j < len(command) and depth:
                depth += {"(": 1, ")": -1}.get(command[j], 0)
                j += 1
            found.append(command[i + 2:j - 1])
            i = j
            continue
        elif char == "`":
            end = command.find("`", i + 1)
            if end != -1:
                found.append(command[i + 1:end])
                i = end + 1
                continue
        i += 1
    return found


def tokenize(command):
    """Segments (lists of tokens) the shell would run one after another."""
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        # Unbalanced quoting: fall back to plain splitting rather than give up.
        tokens = re.findall(r"&&|\|\||[;|&()]|[^\s;|&()]+", command)
    segments, current, skip_next = [], [], False
    for index, token in enumerate(tokens):
        if skip_next:
            skip_next = False
            continue
        if token in SEPARATORS:
            if current:
                segments.append(current)
            current = []
            continue
        if token in REDIRECTS:
            skip_next = True  # the redirect's target is not an argument
            continue
        nxt = tokens[index + 1] if index + 1 < len(tokens) else ""
        if token.isdigit() and nxt in REDIRECTS:
            continue  # the fd number in `2>/dev/null`
        current.append(token)
    if current:
        segments.append(current)
    return segments


def unwrap(tokens):
    """Drop leading assignments and wrappers such as sudo, env and nohup."""
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token):
            i += 1
            continue
        if os.path.basename(token) in WRAPPERS:
            name = os.path.basename(token)
            i += 1
            while i < len(tokens) and tokens[i].startswith("-"):
                takes_value = tokens[i] in {"-u", "-g", "-U", "-C", "-n", "-s", "-k"}
                i += 2 if takes_value else 1
            if name == "timeout" and i < len(tokens) and re.match(r"^\d", tokens[i]):
                i += 1
            continue
        break
    return tokens[i:]


def commands_in(command, depth=0):
    """Every command (token list) this line would run, with the heredoc bodies
    fed to each. Recurses into `bash -c`, `eval` and command substitutions."""
    if depth > 4:
        return []
    command = command.replace("\\\n", " ")
    stripped, bodies = split_heredocs(command)
    found = []
    for segment in tokenize(mask_newlines(stripped)):
        tokens = unwrap(segment)
        if not tokens:
            continue
        program = os.path.basename(tokens[0])
        if program in SHELLS and "-c" in tokens[1:]:
            position = tokens.index("-c")
            if position + 1 < len(tokens):
                found += commands_in(tokens[position + 1], depth + 1)
            continue
        if program == "eval":
            found += commands_in(" ".join(tokens[1:]), depth + 1)
            continue
        found.append((tokens, []))
    for inner in substitutions(stripped):
        found += commands_in(inner, depth + 1)
    for opener, body in bodies:
        opener_segments = [unwrap(s) for s in tokenize(opener) if unwrap(s)]
        runs_shell = any(os.path.basename(s[0]) in SHELLS for s in opener_segments)
        if runs_shell:
            found += commands_in(body, depth + 1)
        else:
            # Data for a program: attach it, so a database client's input is
            # still read for SQL.
            for segment in opener_segments:
                found.append((segment, [body]))
    return found


# --------------------------------------------------------------------------
# Checks, one command at a time
# --------------------------------------------------------------------------

def outside_project(target, root):
    """True when this path resolves outside the project directory."""
    if not target or "$" in target or "`" in target or target.startswith("~"):
        return True
    try:
        path = Path(target)
        resolved = (path if path.is_absolute() else root / path).resolve()
    except Exception:
        return True
    return root != resolved and root not in resolved.parents


def short_flags(args):
    """Letters of every single-dash flag cluster: -Rf → {'R', 'f'}."""
    letters = set()
    for arg in args:
        if re.match(r"^-[A-Za-z]+$", arg):
            letters.update(arg[1:])
    return letters


def check_rm(tokens, root):
    args = tokens[1:]
    if "--" in args:
        split = args.index("--")
        flags, targets = args[:split], args[split + 1:]
    else:
        flags = [a for a in args if a.startswith("-")]
        targets = [a for a in args if not a.startswith("-")]
    recursive = "--recursive" in flags or bool(short_flags(flags) & {"r", "R"})
    if not recursive:
        return None
    for target in targets:
        if outside_project(target, root):
            return (
                f"`rm -r {clip(target)}` deletes outside the project ({root}). "
                "Agents may only delete inside the project they were given.\n"
                "Do not retry with another way of deleting (find -delete, rm "
                "without -r, a script). If you meant a path inside the project, "
                "use a path relative to it. If it really is outside, give the "
                "user the exact command and the reason, and let them run it."
            )
    return None


def check_find(tokens, root):
    args = tokens[1:]
    deletes = "-delete" in args or any(
        a in {"-exec", "-execdir"} and i + 1 < len(args) and os.path.basename(args[i + 1]) == "rm"
        for i, a in enumerate(args))
    if not deletes:
        return None
    starts = []
    for arg in args:
        if arg.startswith(("-", "(", "!")):
            break
        starts.append(arg)
    for start in starts or ["."]:
        if outside_project(start, root):
            return (
                f"`find {clip(start)} … -delete` deletes outside the project "
                f"({root}). Agents may only delete inside the project.\n"
                "Give the user the exact command and the reason, and let them run it."
            )
    return None


def tracked_changes(root):
    """Modified tracked files; untracked files survive reset and checkout."""
    status = git(root, "status", "--porcelain", "--untracked-files=no")
    return [line[3:] for line in status.splitlines()] if status else []


def git_subcommand(tokens):
    i = 1
    while i < len(tokens) and tokens[i].startswith("-"):
        takes_value = tokens[i] in {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
        i += 2 if takes_value else 1
    return (tokens[i], tokens[i + 1:]) if i < len(tokens) else (None, [])


def check_push(args, root):
    letters = short_flags(args)
    forced = bool({"--force", "--force-with-lease", "--force-if-includes"} & set(args)) \
        or any(a.startswith("--force-with-lease=") for a in args) or "f" in letters
    deleting = "--delete" in args or "d" in letters
    if "--mirror" in args:
        return (
            "`git push --mirror` makes the remote match this clone exactly, "
            "overwriting and deleting its branches, including protected ones.\n"
            "Push the branches you mean by name instead."
        )
    positional = [a for a in args if not a.startswith("-")]
    refspecs = positional[1:]
    if not refspecs:
        current = git(root, "rev-parse", "--abbrev-ref", "HEAD")
        refspecs = [current] if current else []
    for refspec in refspecs:
        plus = refspec.startswith("+")
        spec = refspec.lstrip("+")
        source, _, destination = spec.partition(":") if ":" in spec else (spec, "", spec)
        branch = destination.replace("refs/heads/", "", 1)
        if branch not in PROTECTED_BRANCHES:
            continue
        if deleting or (":" in spec and not source):
            return (
                f"This deletes the remote branch {branch}, which other people "
                "build on.\nDo not retry another way. If it must go, tell the "
                "user why and let them delete it."
            )
        if forced or plus:
            return (
                f"Force-pushing to {branch} rewrites history other people have "
                "already pulled; --force-with-lease rewrites it too, so it is "
                "not an alternative.\n"
                f"Push to a new branch instead (git push -u origin HEAD:{branch}-rewrite) "
                f"and tell the user; if {branch} itself must be rewritten, ask "
                "the user to do it."
            )
    return None


def check_git(tokens, root):
    subcommand, args = git_subcommand(tokens)
    letters = short_flags(args)
    if subcommand == "push":
        return check_push(args, root)

    if subcommand == "reset" and "--hard" in args:
        changed = tracked_changes(root)
        if changed:
            listed = ", ".join(changed[:5]) + (" …" if len(changed) > 5 else "")
            return (
                f"`git reset --hard` would discard {len(changed)} modified "
                f"tracked file(s): {clip(listed)}. Retrying the same command "
                "will be blocked again.\n"
                'Run git stash push -m "before reset: <why>" first and then '
                "retry: the stash is the undo."
            )

    if subcommand in {"checkout", "restore"}:
        discards_all = any(a in {".", ":/", "*", ":(top)"} for a in args) or \
            (subcommand == "checkout" and ("--force" in args or "f" in letters))
        if discards_all:
            changed = tracked_changes(root)
            if changed:
                return (
                    f"`git {subcommand} {clip(' '.join(args))}` discards all "
                    f"{len(changed)} uncommitted change(s).\n"
                    'Run git stash push -m "<why>" first, or restore only the '
                    "files you mean: git restore -- <file>."
                )

    if subcommand == "clean":
        dry_run = "--dry-run" in args or "n" in letters
        if not dry_run and ("--force" in args or "f" in letters):
            return (
                f"`git clean {clip(' '.join(args))}` permanently deletes "
                "untracked files, which git has no copy of.\n"
                "Run git clean -n with the same flags and show the user the "
                "list; delete specific build outputs inside the project with "
                "rm -r <path>; otherwise ask the user to run the clean."
            )

    if subcommand == "branch":
        force_delete = "D" in letters or (
            ("--delete" in args or "d" in letters) and ("--force" in args or "f" in letters))
        if force_delete:
            return (
                "`git branch -D` deletes a branch even if its commits are "
                "merged nowhere.\nUse git branch -d <name>; if it refuses, the "
                "branch has unmerged work, so tell the user instead of forcing it."
            )
    return None


def check_misc(tokens):
    program = os.path.basename(tokens[0])
    args = tokens[1:]
    if program.startswith("mkfs") or (
            program == "dd" and any(a.startswith("of=/dev/") for a in args)):
        return (
            "This writes directly to a block device and destroys its "
            "filesystem. Agents never run this.\n"
            "Give the user the exact command and its purpose, and stop."
        )
    if program == "chmod" and any(a in {"777", "0777", "a+rwx"} for a in args):
        target = next((a for a in args if not a.startswith("-") and a not in {"777", "0777", "a+rwx"}), "")
        return (
            f"`chmod 777` makes {clip(target) or 'the target'} world-writable.\n"
            "Use 755 for directories and executables, 644 for files, or u+x "
            "to add execute for the owner only."
        )
    if program == "kubectl" and "delete" in args:
        bulk = any(a in {"--all", "-A", "--all-namespaces", "namespace", "namespaces", "ns"}
                   or a.startswith(("namespace/", "ns/")) for a in args)
        context = [args[i + 1] for i, a in enumerate(args[:-1])
                   if a in {"--context", "-n", "--namespace"}]
        context += [a.split("=", 1)[1] for a in args
                    if a.startswith(("--context=", "--namespace=", "-n="))]
        if bulk and not any(TEST_MARKER.search(c) for c in context):
            return (
                "This bulk-deletes Kubernetes resources, and no context or "
                "namespace in the command is a non-production one.\n"
                "List them with kubectl get, then delete specific ones by name "
                "(kubectl delete <kind> <name> -n <ns>), or ask the user to run "
                "the bulk delete."
            )
    if program == "terraform" and args[:1] and args[0] in {"apply", "destroy"} and \
            any(a in {"-auto-approve", "--auto-approve"} for a in args):
        return (
            f"`terraform {args[0]} -auto-approve` changes infrastructure with "
            "nobody reading the plan. Without the flag Terraform waits for a "
            "typed \"yes\" this shell cannot give, so do not retry without it.\n"
            "Run terraform plan -out=tfplan (add -destroy to destroy), show the "
            "user the summary, and only after they approve run terraform apply tfplan."
        )
    return None


SQL_DESTRUCTIVE = re.compile(r"\b(DROP\s+(?:TABLE|DATABASE|SCHEMA)|TRUNCATE)\b", re.I)


def destructive_sql(text):
    """The first destructive statement in this SQL text, or None."""
    for statement in text.split(";"):
        match = SQL_DESTRUCTIVE.search(statement)
        if match:
            return statement.strip()
        if re.search(r"\bDELETE\s+FROM\b", statement, re.I) and \
                not re.search(r"\bWHERE\b", statement, re.I):
            return statement.strip()
    return None


def check_sql(tokens, bodies):
    if not any(os.path.basename(t) in DB_CLIENTS for t in tokens):
        return None
    for text in [t for t in tokens] + bodies:
        statement = destructive_sql(text)
        if not statement:
            continue
        context = [t for t in tokens if t != text and not destructive_sql(t)]
        if any(TEST_MARKER.search(t) for t in context):
            return None
        return (
            f"`{clip(statement)}` is irreversible, and nothing in the "
            "connection arguments names a test or local database.\n"
            "Do not add words like \"test\" or \"local\" to get past this check. "
            "Tell the user which database and table you intend to change and "
            "ask them to confirm and run it, or write a migration and leave "
            "running it to the user."
        )
    return None


def check(tokens, bodies, root):
    program = os.path.basename(tokens[0])
    if program == "rm":
        return check_rm(tokens, root)
    if program == "find":
        return check_find(tokens, root)
    if program == "git":
        return check_git(tokens, root)
    return check_sql(tokens, bodies) or check_misc(tokens)


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0

    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return 0

    root = project_root(payload)
    rules = allowlist(root)

    for tokens, bodies in commands_in(command):
        text = " ".join(tokens)
        if any(rule.search(text) for rule in rules):
            continue
        reason = check(tokens, bodies, root)
        if reason:
            print(f"Blocked by guard_destructive: {reason}", file=sys.stderr)
            return 2

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
