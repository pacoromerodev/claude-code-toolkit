#!/usr/bin/env python3
"""Which eval cases have never been measured, and which changed since.

A suite nobody runs decays quietly: the case is edited, the number stays, and
the number is quoted. This does not measure anything — it cannot, the
measurement costs money — but it makes the gap impossible to miss, which is
the part that failed before.

Four states per case, from the plugin's `evals/measurements.json`:

  measured   the recorded fingerprint matches the case on disk
  stale      the case has been edited since it was measured
  nobase     current fingerprint, but no baseline: every no-plugin run
             errored, so the score has nothing to be compared against
  never      no entry at all

A score without a baseline is not a measurement of what the plugin adds, which
is the only number this ledger exists for. It is listed with the stale ones.

Usage: check_eval_freshness.py [--enforce] [--list-stale] [repository root]

Report-only by default; --enforce exits 1 when anything is stale or never
measured. Report-only is the honest default here: the runs are manual, so a
red build would only teach people to ignore red builds.

--list-stale prints `plugin/case` for everything without a current
measurement, one per line and nothing else. `run-evals.sh --stale` reads it,
which turns re-measuring from a full pass into whatever actually changed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_ledger import case_fingerprint, read_ledger  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]


def main(argv):
    enforce = "--enforce" in argv
    listing = "--list-stale" in argv
    rest = [a for a in argv[1:] if not a.startswith("--")]
    root = Path(rest[0]).resolve() if rest else ROOT

    rows, stale, nobase, never = [], [], [], []
    for plugin in sorted(p for p in (root / "plugins").glob("*/") if p.is_dir()):
        ledger = read_ledger(plugin)
        for case_dir in sorted((plugin / "evals").glob("*/")):
            if not (case_dir / "case.yaml").is_file():
                continue
            name = case_dir.name
            entry = ledger.get(name)
            if not entry:
                rows.append((plugin.name, name, "never", ""))
                never.append(f"{plugin.name}/{name}")
                continue
            if entry.get("fingerprint") != case_fingerprint(case_dir):
                rows.append((plugin.name, name, "stale",
                             f"measured {entry.get('measured', '?')}"))
                stale.append(f"{plugin.name}/{name}")
                continue
            if entry.get("delta") is None:
                rows.append((plugin.name, name, "nobase",
                             f"{entry.get('score')} vs no baseline  on "
                             f"{entry.get('measured', '?')}"))
                nobase.append(f"{plugin.name}/{name}")
                continue
            detail = f"{entry.get('score')} vs {entry.get('baseline')}"
            rows.append((plugin.name, name, "measured",
                         f"{detail}  on {entry.get('measured', '?')}"))

    if listing:
        for plugin, name, state, _ in rows:
            if state != "measured":
                print(f"{plugin}/{name}")
        return 0

    width = max((len(f"{p}/{c}") for p, c, _, _ in rows), default=10)
    for plugin, name, state, detail in rows:
        mark = {"measured": "ok   ", "stale": "STALE", "nobase": "NOBAS",
                "never": "never"}[state]
        print(f"{mark}  {f'{plugin}/{name}':<{width}}  {detail}")

    print()
    measured = len(rows) - len(stale) - len(nobase) - len(never)
    print(f"{len(rows)} case(s): {measured} measured, {len(stale)} changed "
          f"since, {len(nobase)} without a baseline, {len(never)} never run")

    if not stale and not nobase and not never:
        return 0
    print("\nA case with no current measurement is a case whose number nobody "
          "should quote. Run it: scripts/run-evals.sh <plugin>")
    return 1 if enforce else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
