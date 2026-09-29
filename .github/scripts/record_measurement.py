#!/usr/bin/env python3
"""Write an eval run's scores into the plugin's ledger.

    record_measurement.py [--model <id>] [--judge <id>] <plugin dir> <result.json> [...]

Takes the JSON `claude plugin eval --json` writes and records, per case, what
it scored with the plugin, what the no-plugin arm scored, the delta, how many
runs stood behind it, and fingerprints of the case and of the components it
exercises, as they were.

A run whose arms errored — a usage limit, a missing sandbox, a credential that
the API rejected — is not a measurement and is not recorded. Those failures
score 0.00 in the file, which is indistinguishable from a plugin that failed,
and writing them down would put a lie in the ledger.

The model the runs used is recorded when --model names it. The result file
does not say, and an alias such as `opus` resolves to a different model after
an update: two passes a day apart were once recorded side by side on what
were almost certainly two models, with nothing in the ledger to tell them
apart.

The judge that graded the runs is recorded the same way, with --judge: a
score is the judge's reading as much as the model's answer.

`scripts/run-evals.sh` calls this. Exit 0 when the ledger is written.
"""
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_ledger import (  # noqa: E402
    case_fingerprint, component_fingerprint, read_ledger, write_ledger)


def run_failed(run):
    if run.get("error"):
        return True
    for grader in run.get("graders") or []:
        text = json.dumps(grader)
        if "grader threw" in text or "judge call failed" in text:
            return True
    return False


def arm_mean(runs):
    """(mean score, runs that counted) over the runs that actually happened."""
    good = [r for r in runs if not run_failed(r)]
    if not good:
        return None, 0
    return sum(r.get("score") or 0 for r in good) / len(good), len(good)


def take_option(argv, flag):
    """(value, argv without the flag and its value); value None when absent."""
    if flag not in argv:
        return None, argv
    at = argv.index(flag)
    value = argv[at + 1] if at + 1 < len(argv) else None
    return value, argv[:at] + argv[at + 2:]


def main(argv):
    model, argv = take_option(argv, "--model")
    judge, argv = take_option(argv, "--judge")
    if len(argv) < 3:
        print(__doc__.strip().splitlines()[2].strip())
        return 1

    plugin_dir = Path(argv[1]).resolve()
    cases = read_ledger(plugin_dir)
    recorded, skipped = [], []

    for raw in argv[2:]:
        path = Path(raw)
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            continue

        for case in data.get("cases", []):
            name = case.get("name")
            arms = case.get("arms") or {}
            with_score, with_runs = arm_mean(arms.get("with", []))
            base_score, base_runs = arm_mean(arms.get("without", []))
            if with_score is None:
                skipped.append(name)
                continue

            case_dir = plugin_dir / "evals" / name
            entry = {
                "score": round(with_score, 2),
                "runs": with_runs,
                "measured": date.today().isoformat(),
            }
            if base_score is not None:
                entry["baseline"] = round(base_score, 2)
                entry["delta"] = round(with_score - base_score, 2)
                entry["baselineRuns"] = base_runs
            if model:
                entry["model"] = model
            if judge:
                entry["judge"] = judge
            if case_dir.is_dir():
                entry["fingerprint"] = case_fingerprint(case_dir)
                components = component_fingerprint(plugin_dir, case_dir)
                if components:
                    entry["components"] = components
            cases[name] = entry
            recorded.append(name)

    if not recorded and not skipped:
        print("Nothing to record: no case results in those files.")
        return 0

    path = write_ledger(plugin_dir, cases)
    print(f"Recorded {len(recorded)} case(s) in {path}")
    if skipped:
        print(f"Not recorded, because every run errored: {', '.join(sorted(skipped))}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
