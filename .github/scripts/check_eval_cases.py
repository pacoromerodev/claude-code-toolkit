#!/usr/bin/env python3
"""Every eval case can pass, declares what it needs, and is graded both ways.

`claude plugin eval` runs whatever it finds. A case that cannot pass does not
fail loudly: it scores zero in both arms and looks like a plugin that does not
help. The audit found two such cases (no fixture at all), graders that failed
correct answers because they only said what scores badly, and cases that
silently needed Bash on a machine where Bash-granting evals cannot run.

For every plugins/<plugin>/evals/<case>/ this checks that:

  - the case is a case.yaml (the older prompt.md form had no scaffold hook,
    and both cases written that way could never pass)
  - `name` matches the directory
  - a named scaffold_script exists
  - a case whose allowed_tools include Bash carries the `needs-bash` tag, so
    a runner can skip it honestly instead of scoring it degraded
  - a positive case (no `negative` tag) runs at least 3 times
  - every llm grader says both what scores well and what scores badly

Usage: check_eval_cases.py [root]      (default: the repository root)
Exit 0 when every case passes, 1 otherwise.
"""
import re
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[2]
MIN_POSITIVE_RUNS = 3


def list_field(text, key):
    match = re.search(rf"^\s*{key}:\s*\[(.*)\]\s*$", text, re.M)
    if not match:
        return None
    return [item.strip() for item in match.group(1).split(",") if item.strip()]


def scalar_field(text, key):
    match = re.search(rf"^\s*{key}:\s*(\S.*?)\s*$", text, re.M)
    return match.group(1).strip("\"'") if match else None


def check_case(root, case_dir, problems):
    rel = case_dir.relative_to(root).as_posix()
    case_file = case_dir / "case.yaml"

    if not case_file.is_file():
        if (case_dir / "prompt.md").is_file():
            problems.append(f"{rel}: uses prompt.md; write a case.yaml with a scaffold_script")
        else:
            problems.append(f"{rel}: no case.yaml")
        return

    text = case_file.read_text(encoding="utf-8")

    name = scalar_field(text, "name")
    if name != case_dir.name:
        problems.append(f"{rel}: name is {name!r} but the directory is {case_dir.name!r}")

    scaffold = scalar_field(text, "scaffold_script")
    if scaffold and not (case_dir / scaffold).is_file():
        problems.append(f"{rel}: scaffold_script {scaffold!r} does not exist")

    tags = list_field(text, "tags") or []
    tools = list_field(text, "allowed_tools") or []
    if "Bash" in tools and "needs-bash" not in tags:
        problems.append(f"{rel}: allows Bash but is not tagged needs-bash")

    runs = scalar_field(text, "runs")
    runs = int(runs) if runs and runs.isdigit() else 1
    if "negative" not in tags and runs < MIN_POSITIVE_RUNS:
        problems.append(
            f"{rel}: a positive case runs {runs} time(s); it needs at least "
            f"{MIN_POSITIVE_RUNS}, or one flip decides the result")

    graders = sorted((case_dir / "graders").glob("*.md"))
    if not graders:
        problems.append(f"{rel}: no graders")
    for grader in graders:
        body = grader.read_text(encoding="utf-8")
        if scalar_field(body, "type") != "llm":
            continue
        lowered = body.lower()
        missing = [side for side in ("score well", "score badly") if side not in lowered]
        if missing:
            problems.append(
                f"{rel}/graders/{grader.name}: no \"{missing[0]}\" section; a "
                f"judge told only one side fails answers it should pass")


def main(argv):
    root = (Path(argv[1]) if len(argv) > 1 else DEFAULT_ROOT).resolve()
    problems = []
    cases = sorted(p for p in root.glob("plugins/*/evals/*") if p.is_dir() and p.name != "results")
    for case_dir in cases:
        check_case(root, case_dir, problems)

    if problems:
        print("Eval case check failed:\n")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print(f"OK — {len(cases)} eval case(s) are runnable and graded both ways")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
