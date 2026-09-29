#!/usr/bin/env python3
"""Audit a CLAUDE.md for the reasons its rules get ignored.

    python3 check_claude_md.py CLAUDE.md
    python3 check_claude_md.py . --json

CLAUDE.md is read, not executed. Every line in it competes with every other
line for attention, and it is present in full on every single turn. So the
failure modes are about weight and checkability, not syntax:

  - Length. The longer it gets, the less of it survives.
  - Vagueness. A rule nobody can verify was followed is not a rule.
  - Emphasis inflation. When everything is IMPORTANT, nothing is.
  - Prohibitions with no alternative. "Don't use X" leaves the next move open.
  - Imports. `@file` is expanded inline — it does not save context.

Exit 1 on an error, 0 otherwise.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SOFT_LIMIT = 200
HARD_LIMIT = 400

EMPHASIS = re.compile(r"\b(IMPORTANT|CRITICAL|ALWAYS|NEVER|MUST|MANDATORY|REQUIRED)\b")
EMPHASIS_BUDGET = 10

# Words that promise a standard while naming none.
VAGUE = (
    "properly", "correctly", "appropriately", "as needed", "when appropriate",
    "good practice", "best practice", "best practices", "clean code",
    "well-structured", "reasonable", "sensible", "make sure it's good",
    "high quality", "idiomatic", "where possible", "if necessary",
)

PROHIBITION = re.compile(
    r"^\s*[-*]?\s*(?:do\s+not|don't|never|avoid)\b(.{0,120})", re.I)

# What counts as naming the alternative. Deliberately generous: a rule that
# points somewhere — with an explicit "instead", with a positive imperative, or
# by carving out the acceptable form ("never X without Y", "unless") — is doing
# its job. Flagging those makes the audit noise, and a noisy audit is ignored.
ALTERNATIVE = re.compile(
    r"(\binstead\b|\brather than\b|\bin its place\b|\breplace it with\b"
    r"|\bin favour of\b|\bunless\b|\bexcept when\b|\bif one is\b"
    r"|\bif it is\b|\bwithout\s+(?:either\s+)?[\w-]+"
    r"|\b(?:use|prefer|read|return|writ|call|put|keep|mov|extract|add|set"
    r"|ask|rais|re-rais|logg?|pass|inject|wrap|open|send|route)\w*)", re.I)

IMPORT_LINE = re.compile(r"^\s*@([^\s]+)\s*$")

# A prohibition about an action a hook can see before it happens. CLAUDE.md is
# read by a model that may or may not follow it; a PreToolUse hook is not.
ENFORCEABLE = re.compile(
    r"\b(?:never|don't|do\s+not|under\s+no\s+circumstances)\b[^.]{0,80}?"
    r"\b(push|force[- ]push|commit|merge|rebase|rm\b|delete|drop|truncate"
    r"|deploy|publish|release|chmod|curl|pip\s+install|npm\s+install)\b",
    re.I)

# Where the file's own emphasis sits. A rule that must hold belongs at the top,
# and is worth repeating at the end: the middle of a long file is where
# instructions go quiet.
PLACEMENT_MIN_LINES = 60
EDGE_FRACTION = 0.2


class Finding:
    def __init__(self, level, line, rule, message, hint):
        self.level, self.line, self.rule = level, line, rule
        self.message, self.hint = message, hint

    def as_dict(self):
        return {"level": self.level, "line": self.line, "rule": self.rule,
                "message": self.message, "hint": self.hint}


def in_code_fence(lines):
    """Which lines sit inside a fenced block — code is exempt from prose rules."""
    inside, flags = False, []
    for line in lines:
        if line.lstrip().startswith("```"):
            inside = not inside
            flags.append(True)
            continue
        flags.append(inside)
    return flags


def audit(path, findings):
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    fenced = in_code_fence(lines)
    prose = [l for l, f in zip(lines, fenced) if not f]

    # --- length ---
    count = len([l for l in lines if l.strip()])
    if count > HARD_LIMIT:
        findings.append(Finding(
            "error", 0, "length",
            f"{count} non-empty lines, over the {HARD_LIMIT} that stays usable",
            "This is present on every turn and competes with the actual task. "
            "Move reference material to files the model reads on demand, and "
            "keep here only what must be true every time."))
    elif count > SOFT_LIMIT:
        findings.append(Finding(
            "warning", 0, "length",
            f"{count} non-empty lines, past the {SOFT_LIMIT} where rules start "
            f"getting skipped",
            "Cut the parts that are documentation rather than instruction."))

    # --- emphasis as a budget ---
    hits = [(i + 1, m.group(1)) for i, line in enumerate(lines)
            if not fenced[i] for m in EMPHASIS.finditer(line)]
    if len(hits) > EMPHASIS_BUDGET:
        sample = ", ".join(sorted({word for _, word in hits})[:5])
        findings.append(Finding(
            "warning", hits[EMPHASIS_BUDGET][0], "emphasis",
            f"{len(hits)} emphasis markers ({sample})",
            "Emphasis is a budget. Past about ten, none of it signals anything "
            "— spend it only on the handful of rules that must win over the rest."))

    # --- vague standards ---
    for i, line in enumerate(lines):
        if fenced[i]:
            continue
        lowered = line.lower()
        for word in VAGUE:
            if word in lowered:
                findings.append(Finding(
                    "warning", i + 1, "vague",
                    f"{word!r} promises a standard without naming one",
                    "Write what a reviewer could check: not \"handle errors "
                    "properly\" but \"never catch an exception without either "
                    "re-raising it or logging it with the failing input\"."))
                break

    # --- prohibitions with no alternative ---
    for i, line in enumerate(lines):
        if fenced[i] or not line.strip():
            continue
        match = PROHIBITION.match(line)
        if not match:
            continue
        # Look for the alternative only AFTER the prohibition itself: "Don't
        # use field injection" contains "use", and matching that would call
        # every prohibition satisfied.
        # Drop the prohibition's own verb and object — four words is enough
        # to clear "use" in "Don't use field injection" while keeping the
        # carve-out in "never X without either Y or Z".
        rest = line[match.start(1):].split()
        tail = " ".join(rest[4:])
        # A second sentence on the same line is the alternative more often
        # than not ("Never push to main. Open a pull request."), and the
        # four-word skip above would eat its opening verb.
        sentences = line[match.start(1):].split(". ")
        following = ". ".join(sentences[1:]) if len(sentences) > 1 else ""
        window = " ".join([tail, following] + lines[i + 1:i + 3])
        if not ALTERNATIVE.search(window):
            findings.append(Finding(
                "warning", i + 1, "no-alternative",
                "prohibition with no alternative named",
                "A rule that closes one door and opens none gets worked "
                "around. Say what to do instead, on the same line."))

    # --- rules a hook could enforce ---
    for i, line in enumerate(lines):
        if fenced[i]:
            continue
        match = ENFORCEABLE.search(line)
        if match:
            findings.append(Finding(
                "info", i + 1, "hook-candidate",
                f"a rule about {match.group(1).lower()!r} that only asks",
                "This file is advice the model weighs against everything else "
                "in its context. If it must hold every time, a PreToolUse "
                "hook that exits 2 is what holds it — and the rule can then "
                "come out of here."))

    # --- placement of what must hold ---
    if count >= PLACEMENT_MIN_LINES and hits:
        edge = max(1, int(len(lines) * EDGE_FRACTION))
        if all(edge < number < len(lines) - edge for number, _ in hits):
            findings.append(Finding(
                "warning", hits[0][0], "placement",
                f"every emphasised rule sits in the middle of a "
                f"{count}-line file",
                "The opening and the closing lines are the parts that survive "
                "a long turn. Put what must hold first, and repeat it at the "
                "end; the middle is where instructions go quiet."))

    # --- imports ---
    for i, line in enumerate(lines):
        if fenced[i]:
            continue
        match = IMPORT_LINE.match(line)
        if match:
            target = match.group(1)
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                findings.append(Finding(
                    "error", i + 1, "broken-import",
                    f"imports {target}, which does not exist",
                    "The import silently contributes nothing."))
            else:
                try:
                    imported = len(resolved.read_text(encoding="utf-8").split("\n"))
                except Exception:
                    imported = 0
                if imported > SOFT_LIMIT:
                    findings.append(Finding(
                        "warning", i + 1, "large-import",
                        f"imports {target} ({imported} lines), which is "
                        f"expanded inline",
                        "An @import does not save context — it is spliced in "
                        "whole. Splitting a long file across imports changes "
                        "nothing about its cost."))

    # --- structure ---
    if not any(line.startswith("#") for line in prose):
        findings.append(Finding(
            "warning", 0, "structure",
            "no headings",
            "Headings are what let a rule be found and followed rather than "
            "skimmed past."))

    paragraphs = [l for l, f in zip(lines, fenced)
                  if not f and len(l.strip()) > 220]
    if paragraphs:
        findings.append(Finding(
            "warning", lines.index(paragraphs[0]) + 1, "prose-block",
            f"{len(paragraphs)} very long paragraph(s)",
            "Rules survive as short bullets. Prose reads as background and "
            "gets treated as background."))

    return count


def find_files(paths):
    files = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            for name in ("CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md"):
                candidate = path / name
                if candidate.is_file():
                    files.append(candidate)
        elif path.is_file():
            files.append(path)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", default=["."])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    files = find_files(args.paths or ["."])
    if not files:
        print("No CLAUDE.md found.")
        return 0

    findings, total = [], 0
    for path in files:
        try:
            total += audit(path, findings)
        except Exception as error:
            findings.append(Finding("error", 0, "unreadable",
                                    f"cannot read {path}: {error}", ""))

    errors = [f for f in findings if f.level == "error"]

    if args.json:
        print(json.dumps({
            "files": [str(f) for f in files],
            "lines": total,
            "errors": len(errors),
            "findings": [f.as_dict() for f in findings],
        }, indent=2))
        return 1 if errors else 0

    order = {"error": 0, "warning": 1, "info": 2}
    for finding in sorted(findings, key=lambda f: (order.get(f.level, 1), f.line)):
        mark = {"error": "ERROR", "info": "note "}.get(finding.level, "warn ")
        where = f"line {finding.line}" if finding.line else "file"
        print(f"{mark}  {where}  [{finding.rule}]")
        print(f"        {finding.message}")
        if finding.hint:
            print(f"        → {finding.hint}")

    notes = [f for f in findings if f.level == "info"]
    print()
    if not findings:
        print(f"Clean — {total} lines, nothing to report.")
    elif not errors and len(notes) == len(findings):
        print(f"Clean — {total} lines, {len(notes)} note(s) worth a look.")
    else:
        print(f"{total} lines: {len(errors)} error(s), "
              f"{len(findings) - len(errors) - len(notes)} warning(s), "
              f"{len(notes)} note(s)")

    return 1 if errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
