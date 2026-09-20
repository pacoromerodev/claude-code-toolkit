#!/usr/bin/env python3
"""Check a database migration for the operations that break a running deploy.

    python3 check_migration.py src/main/resources/db/migration
    python3 check_migration.py V12__add_index.sql --json

Handles Flyway SQL and Liquibase XML/YAML. The rule behind every check is the
same: during a rolling deploy the old code and the new code run at the same
time, against one schema. An operation is unsafe when it breaks the version
that has not been replaced yet, or when it holds a lock long enough to matter.

Exit 1 when anything unsafe is found, 0 otherwise. This is the mechanical half
of a migration review — it catches the known shapes, not whether the change
makes sense.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SQL_SUFFIXES = {".sql"}
LIQUIBASE_SUFFIXES = {".xml", ".yaml", ".yml"}


class Issue:
    def __init__(self, level, file, line, rule, message, fix):
        self.level = level
        self.file = file
        self.line = line
        self.rule = rule
        self.message = message
        self.fix = fix

    def as_dict(self):
        return {
            "level": self.level, "file": self.file, "line": self.line,
            "rule": self.rule, "message": self.message, "fix": self.fix,
        }


def strip_comments(sql):
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    return "\n".join(line.split("--")[0] for line in sql.split("\n"))


def line_of(text, index):
    return text[:index].count("\n") + 1


def check_sql(path, raw, issues):
    text = strip_comments(raw)
    name = path.name
    postgres = not re.search(r"\bENGINE\s*=\s*InnoDB\b", text, re.I)

    # --- index creation that locks writes ---
    for match in re.finditer(r"\bCREATE\s+(UNIQUE\s+)?INDEX\b(?!\s+CONCURRENTLY)", text, re.I):
        if postgres:
            issues.append(Issue(
                "error", name, line_of(text, match.start()), "index-lock",
                "CREATE INDEX without CONCURRENTLY takes an exclusive lock on "
                "writes for the whole build",
                "CREATE INDEX CONCURRENTLY — and run it outside a transaction, "
                "which in Flyway means a separate script with no wrapping "
                "transaction."))

    # --- NOT NULL without a default on an existing table ---
    for match in re.finditer(
        r"\bALTER\s+TABLE\s+(\S+)\s+ADD\s+(?:COLUMN\s+)?(\S+)[^;]*?\bNOT\s+NULL\b([^;]*)",
        text, re.I,
    ):
        tail = match.group(3) or ""
        if not re.search(r"\bDEFAULT\b", match.group(0), re.I):
            issues.append(Issue(
                "error", name, line_of(text, match.start()), "not-null-no-default",
                f"adds NOT NULL column {match.group(2)} to existing table "
                f"{match.group(1)} with no default",
                "Either give it a DEFAULT, or do it in three steps: add it "
                "nullable, backfill in batches, then add the constraint."))
        del tail

    for match in re.finditer(
        r"\bALTER\s+TABLE\s+(\S+)\s+ALTER\s+(?:COLUMN\s+)?(\S+)\s+SET\s+NOT\s+NULL",
        text, re.I,
    ):
        issues.append(Issue(
            "warning", name, line_of(text, match.start()), "set-not-null",
            f"sets NOT NULL on {match.group(1)}.{match.group(2)}: this scans "
            f"the whole table, and fails outright if any row is null",
            "Backfill first and verify the count is zero. On Postgres 12+, add "
            "a NOT VALID check constraint, validate it, then set NOT NULL."))

    # --- destructive schema changes with readers still on the old code ---
    for pattern, rule, what in (
        (r"\bALTER\s+TABLE\s+(\S+)\s+DROP\s+(?:COLUMN\s+)?(\S+)", "drop-column", "drops column"),
        (r"\bALTER\s+TABLE\s+(\S+)\s+RENAME\s+(?:COLUMN\s+)?(\S+)", "rename-column", "renames column"),
        (r"\bDROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?(\S+)()", "drop-table", "drops table"),
    ):
        for match in re.finditer(pattern, text, re.I):
            parts = [g.strip().strip(";,()\"'`") for g in match.groups() if g and g.strip()]
            target = ".".join(parts)
            issues.append(Issue(
                "error", name, line_of(text, match.start()), rule,
                f"{what} {target}: the running version of the application is "
                f"still reading it during a rolling deploy",
                "Split across two releases — stop reading it, ship, then drop "
                "it in the next migration. A rename is a drop and an add."))

    # --- type changes that can truncate ---
    for match in re.finditer(
        r"\bALTER\s+TABLE\s+(\S+)\s+ALTER\s+(?:COLUMN\s+)?(\S+)\s+TYPE\s+(\S+)",
        text, re.I,
    ):
        issues.append(Issue(
            "warning", name, line_of(text, match.start()), "type-change",
            f"changes the type of {match.group(1)}.{match.group(2)} to "
            f"{match.group(3)}: rewrites the table and can truncate data",
            "Check whether the new type is strictly wider. If it is not, add a "
            "new column, backfill, swap, drop."))

    # --- unbounded DML ---
    for match in re.finditer(r"\b(UPDATE|DELETE\s+FROM)\s+(\S+)((?:(?!;).)*)", text, re.I | re.S):
        body = match.group(3) or ""
        if not re.search(r"\bWHERE\b", body, re.I):
            issues.append(Issue(
                "error", name, line_of(text, match.start()), "unbounded-dml",
                f"{match.group(1).upper()} on {match.group(2)} with no WHERE: "
                f"locks every row and runs for as long as the table is big",
                "Add a predicate and batch it, or move the backfill out of the "
                "migration entirely."))
        elif not re.search(r"\bLIMIT\b|\bBATCH", body, re.I) and \
                re.search(r"\bUPDATE\b", match.group(1), re.I):
            issues.append(Issue(
                "info", name, line_of(text, match.start()), "bulk-update",
                f"bulk UPDATE on {match.group(2)}",
                "On a large table, batch it — one long transaction blocks "
                "everything behind it."))

    # --- locks taken explicitly ---
    if re.search(r"\bLOCK\s+TABLE\b", text, re.I):
        issues.append(Issue(
            "warning", name, 0, "explicit-lock",
            "takes an explicit table lock",
            "Everything queued behind it waits. Be sure the window is short."))

    # --- foreign keys validated immediately ---
    for match in re.finditer(
        r"\bADD\s+CONSTRAINT\s+(\S+)\s+FOREIGN\s+KEY\b((?:(?!;).)*)", text, re.I | re.S
    ):
        if not re.search(r"NOT\s+VALID", match.group(2) or "", re.I):
            issues.append(Issue(
                "warning", name, line_of(text, match.start()), "fk-validate",
                f"adds foreign key {match.group(1)} and validates it in the "
                f"same statement, scanning the whole table under a lock",
                "Add it NOT VALID, then VALIDATE CONSTRAINT separately — that "
                "takes a weaker lock."))


def check_liquibase(path, raw, issues):
    name = path.name
    lowered = raw.lower()

    has_change = "changeset" in lowered
    if not has_change:
        return

    destructive = ("dropcolumn", "droptable", "renamecolumn", "renametable",
                   "modifydatatype")
    for keyword in destructive:
        for match in re.finditer(keyword, lowered):
            issues.append(Issue(
                "error", name, line_of(raw, match.start()), "destructive-change",
                f"<{keyword}> runs while the previous version of the "
                f"application is still deployed",
                "Split it across two releases: stop using the column, ship, "
                "then remove it."))

    if "createindex" in lowered and "concurrent" not in lowered:
        issues.append(Issue(
            "warning", name, 0, "index-lock",
            "createIndex without a concurrent strategy",
            "On Postgres, set runInTransaction=\"false\" and use CREATE INDEX "
            "CONCURRENTLY through <sql>."))

    # Rollback: Liquibase can infer some, never the ones that matter here.
    if "rollback" not in lowered:
        risky = any(k in lowered for k in ("sql", "update", "delete", "insert"))
        if risky:
            issues.append(Issue(
                "warning", name, 0, "no-rollback",
                "changeset has no <rollback> and contains statements Liquibase "
                "cannot reverse on its own",
                "Write the rollback, or state in a comment why this cannot be "
                "rolled back and what the recovery is instead."))


def check_naming(paths, issues):
    """Flyway versions must be unique — a duplicate silently shadows."""
    seen = {}
    for path in paths:
        match = re.match(r"^V(\d+(?:[._]\d+)*)__", path.name)
        if not match:
            if path.suffix in SQL_SUFFIXES and not path.name.startswith(("R__", "U")):
                issues.append(Issue(
                    "warning", path.name, 0, "naming",
                    "does not follow the Flyway V<version>__<description>.sql "
                    "convention",
                    "Rename it, or it may not be picked up in the order you "
                    "expect."))
            continue
        version = match.group(1).replace("_", ".")
        if version in seen:
            issues.append(Issue(
                "error", path.name, 0, "duplicate-version",
                f"reuses version {version}, already taken by {seen[version]}",
                "Flyway refuses to start with two migrations at one version."))
        else:
            seen[version] = path.name


def collect(paths):
    files = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            for suffix in SQL_SUFFIXES | LIQUIBASE_SUFFIXES:
                files.extend(sorted(path.rglob(f"*{suffix}")))
        elif path.is_file():
            files.append(path)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    files = collect(args.paths)
    issues = []
    check_naming(files, issues)

    for path in files:
        try:
            raw = path.read_text(encoding="utf-8", errors="replace")
        except Exception as error:
            issues.append(Issue("warning", path.name, 0, "unreadable",
                                f"cannot read: {error}", "Check permissions."))
            continue
        if path.suffix in SQL_SUFFIXES:
            check_sql(path, raw, issues)
        else:
            check_liquibase(path, raw, issues)

    errors = [i for i in issues if i.level == "error"]

    if args.json:
        print(json.dumps({
            "checked": len(files),
            "errors": len(errors),
            "issues": [i.as_dict() for i in issues],
        }, indent=2))
        return 1 if errors else 0

    if not files:
        print("No migration files found.")
        return 0

    order = {"error": 0, "warning": 1, "info": 2}
    for issue in sorted(issues, key=lambda i: (order[i.level], i.file, i.line)):
        mark = {"error": "UNSAFE", "warning": "check", "info": "note "}[issue.level]
        where = f"{issue.file}:{issue.line}" if issue.line else issue.file
        print(f"{mark}  {where}  [{issue.rule}]")
        print(f"        {issue.message}")
        print(f"        → {issue.fix}")

    print()
    if not issues:
        print(f"Nothing unsafe found in {len(files)} migration file(s).")
    else:
        print(f"{len(files)} file(s): {len(errors)} unsafe, "
              f"{len(issues) - len(errors)} to check")
    print("This covers the known shapes only — it cannot tell whether the "
          "change is the right one.")

    return 1 if errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
