#!/usr/bin/env python3
"""Audit an MCP server for the things that make it unusable by a model.

    python3 check_mcp_server.py server.py
    python3 check_mcp_server.py src/ --json

An MCP server can be correct Python and still be useless: the model picks a
tool by reading its description, so a vague one is the single most common
cause of tool-use failure. The rest of the checks follow the same theme —
everything the model has to guess is a place it will guess wrong.

Parses with `ast`, so it reads the code rather than grepping it. Exit 1 on an
error, 0 otherwise.
"""
import argparse
import ast
import json
import re
import sys
from pathlib import Path

DESCRIPTION_MIN_WORDS = 12

# Words that fill a description without saying anything.
FILLER = re.compile(
    r"^\s*(a |the )?(helper|utility|wrapper|function|tool|method|handler)"
    r"( (for|to|that))?\s*", re.I)

VAGUE_PARAM_NAMES = {"data", "input", "value", "arg", "args", "params",
                     "payload", "obj", "item", "x", "s"}

# Returning everything is how a tool blows up a context window.
UNBOUNDED_HINTS = ("list_all", "get_all", "fetch_all", "dump", "export_all",
                   "read_all", "search")

LONG_RUNNING_HINTS = ("index", "crawl", "sync", "import", "migrate", "scan",
                      "build", "train", "backup", "process_all")


class Finding:
    def __init__(self, level, file, line, rule, message, hint):
        self.level, self.file, self.line, self.rule = level, file, line, rule
        self.message, self.hint = message, hint

    def as_dict(self):
        return {"level": self.level, "file": self.file, "line": self.line,
                "rule": self.rule, "message": self.message, "hint": self.hint}


def decorator_kind(node):
    """'tool', 'resource', 'prompt' — or None when this is a plain function."""
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        name = None
        if isinstance(target, ast.Attribute):
            name = target.attr
        elif isinstance(target, ast.Name):
            name = target.id
        if name in {"tool", "resource", "prompt"}:
            return name, decorator
    return None, None


def decorator_uri(decorator):
    if not isinstance(decorator, ast.Call):
        return None
    for arg in decorator.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
    for keyword in decorator.keywords:
        if keyword.arg in {"uri", "uri_template"} and \
                isinstance(keyword.value, ast.Constant):
            return keyword.value.value
    return None


def has_context_param(node):
    for arg in list(node.args.args) + list(node.args.kwonlyargs):
        annotation = arg.annotation
        if isinstance(annotation, ast.Name) and annotation.id == "Context":
            return True
        if isinstance(annotation, ast.Attribute) and annotation.attr == "Context":
            return True
        if arg.arg in {"ctx", "context"}:
            return True
    return False


def calls_anywhere(node, names):
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            target = child.func
            attr = getattr(target, "attr", None) or getattr(target, "id", None)
            if attr in names:
                return True
    return False


def check_tool(node, kind, decorator, file, findings):
    doc = ast.get_docstring(node) or ""
    body = doc.strip()

    # --- the description ---
    if not body:
        findings.append(Finding(
            "error", file, node.lineno, "no-description",
            f"{kind} `{node.name}` has no docstring",
            "The model picks a tool by reading its description. Without one it "
            "has only the name to go on, which is the most common reason a "
            "tool is never called."))
    else:
        stripped = FILLER.sub("", body)
        words = len(stripped.split())
        # Only tools are held to the long form. A tool is chosen from among
        # several on the strength of its description alone, so it has to draw
        # the boundary. A resource is attached by the application and a prompt
        # is picked by a person from a labelled list — for those, one clear
        # sentence is the right length, and demanding four makes the audit
        # noise.
        minimum = DESCRIPTION_MIN_WORDS if kind == "tool" else 4
        if words < minimum:
            findings.append(Finding(
                "warning", file, node.lineno, "thin-description",
                f"{kind} `{node.name}`: description is {words} useful word(s)",
                "Three or four sentences: what it does, when to use it rather "
                "than a neighbouring tool, what it returns, and what happens "
                "when it fails."))
        lowered = body.lower()
        if kind == "tool" and not any(
            marker in lowered
            for marker in ("use when", "use this", "when the", "returns",
                           "call this", "given", "for retrieving", "to find")
        ):
            findings.append(Finding(
                "warning", file, node.lineno, "no-selection-cue",
                f"tool `{node.name}`: description never says when to choose it",
                "With several tools available, the model needs the boundary — "
                "what this one covers that the others do not."))
        if kind == "tool" and "error" not in lowered and "fail" not in lowered \
                and "raise" not in lowered:
            findings.append(Finding(
                "info", file, node.lineno, "no-failure-mode",
                f"tool `{node.name}`: description says nothing about failure",
                "Say what happens on a missing record or a bad argument, so "
                "the model can tell 'no results' from 'broken'."))

    # --- parameters ---
    for arg in list(node.args.args) + list(node.args.kwonlyargs):
        if arg.arg in {"self", "ctx", "context"}:
            continue
        if arg.annotation is None:
            findings.append(Finding(
                "error", file, node.lineno, "untyped-param",
                f"{kind} `{node.name}`: parameter `{arg.arg}` has no type "
                f"annotation",
                "The schema the model sees is generated from the annotations. "
                "Without one the parameter is untyped and will be guessed."))
        if arg.arg in VAGUE_PARAM_NAMES:
            findings.append(Finding(
                "warning", file, node.lineno, "vague-param",
                f"{kind} `{node.name}`: parameter named `{arg.arg}`",
                "Name it for what it holds. `data` tells the model nothing "
                "about what to put there."))

    annotated = [a for a in list(node.args.args) + list(node.args.kwonlyargs)
                 if a.annotation is not None and a.arg not in {"self", "ctx", "context"}]
    described = sum(
        1 for a in annotated
        if isinstance(a.annotation, ast.Subscript)
        and "Field" in ast.dump(a.annotation)
    )
    if annotated and described == 0 and len(annotated) > 1:
        findings.append(Finding(
            "info", file, node.lineno, "no-field-descriptions",
            f"{kind} `{node.name}`: no parameter carries a Field description",
            "`Annotated[str, Field(description=...)]` puts the explanation in "
            "the schema, where the model actually reads it."))

    # --- result size ---
    if kind == "tool" and any(hint in node.name.lower() for hint in UNBOUNDED_HINTS):
        source = ast.dump(node)
        if "limit" not in source and "max_results" not in source and \
                "page" not in source and "top" not in source:
            findings.append(Finding(
                "warning", file, node.lineno, "unbounded-result",
                f"tool `{node.name}` looks like it returns everything, with no "
                f"limit parameter",
                "One oversized result can fill the context window and end the "
                "session. Add a limit with a sane default, and say in the "
                "description that the result is truncated."))

    # --- progress on long work ---
    if kind == "tool" and any(hint in node.name.lower() for hint in LONG_RUNNING_HINTS):
        if not has_context_param(node):
            findings.append(Finding(
                "info", file, node.lineno, "no-progress",
                f"tool `{node.name}` looks long-running but takes no Context",
                "Take `ctx: Context` and call `await ctx.report_progress(n, "
                "total)`, or the client has no idea whether it is working."))

    # --- secrets in the signature ---
    for arg in list(node.args.args) + list(node.args.kwonlyargs):
        if re.search(r"(api_?key|token|secret|password|credential)", arg.arg, re.I):
            findings.append(Finding(
                "error", file, node.lineno, "secret-parameter",
                f"{kind} `{node.name}`: parameter `{arg.arg}` asks the model "
                f"for a credential",
                "The model does not hold your secrets and should never be "
                "asked to pass one. Read it from the server's environment."))

    # --- filesystem access without a root check ---
    if calls_anywhere(node, {"open", "read_text", "write_text", "read_bytes",
                             "write_bytes", "unlink", "rmtree"}):
        source = ast.dump(node)
        if "is_path_allowed" not in source and "resolve" not in source and \
                "list_roots" not in source:
            findings.append(Finding(
                "error", file, node.lineno, "unchecked-path",
                f"{kind} `{node.name}` touches the filesystem with no path "
                f"check",
                "Roots tell you the boundary; the SDK does not enforce it. "
                "Resolve the path and verify it sits inside an allowed root "
                "before opening anything."))


def check_resource(node, decorator, file, findings):
    uri = decorator_uri(decorator)
    if uri and re.search(r"(key|token|secret|password)=", uri, re.I):
        findings.append(Finding(
            "error", file, node.lineno, "secret-in-uri",
            f"resource `{node.name}`: the URI template carries a credential",
            "Resource URIs are visible to the client and get logged. Keep "
            "secrets out of them."))
    if uri and "{" in uri and not node.args.args:
        findings.append(Finding(
            "warning", file, node.lineno, "template-no-params",
            f"resource `{node.name}`: URI template has placeholders but the "
            f"function takes no arguments",
            "The placeholders are passed as arguments — without them the "
            "template cannot resolve."))


def check_module(path, findings):
    file = path.name
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as error:
        findings.append(Finding("error", file, error.lineno or 0, "syntax",
                                f"cannot parse: {error.msg}", ""))
        return 0

    counts = {"tool": 0, "resource": 0, "prompt": 0}

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        kind, decorator = decorator_kind(node)
        if kind is None:
            continue
        counts[kind] += 1
        check_tool(node, kind, decorator, file, findings)
        if kind == "resource":
            check_resource(node, decorator, file, findings)

    source = path.read_text(encoding="utf-8")

    # stateless_http silently removes half the protocol.
    if "stateless_http=True" in source.replace(" ", ""):
        lost = []
        if "create_message" in source:
            lost.append("sampling")
        if "report_progress" in source:
            lost.append("progress reporting")
        if "subscribe" in source:
            lost.append("subscriptions")
        if lost:
            findings.append(Finding(
                "error", file, 0, "stateless-conflict",
                f"stateless_http=True, but this server uses "
                f"{', '.join(lost)}",
                "Stateless mode drops session ids and every server-to-client "
                "request. Those features stop working — silently. Either run "
                "stateful, or remove them."))
        else:
            findings.append(Finding(
                "info", file, 0, "stateless-note",
                "stateless_http=True",
                "Scales behind a load balancer, at the cost of session ids, "
                "server-to-client requests, sampling, progress and "
                "subscriptions. Make sure none of those are wanted later."))

    if counts["tool"] and not counts["resource"] and "read" in source.lower():
        findings.append(Finding(
            "info", file, 0, "primitive-fit",
            f"{counts['tool']} tool(s) and no resources",
            "Tools are model-controlled and resources are application-"
            "controlled. Read-only context the application chooses to attach "
            "is usually a resource, not a tool."))

    return sum(counts.values())


def collect(paths):
    files = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
        elif path.is_file() and path.suffix == ".py":
            files.append(path)
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    files = collect(args.paths)
    findings, total = [], 0
    for path in files:
        total += check_module(path, findings)

    errors = [f for f in findings if f.level == "error"]

    if args.json:
        print(json.dumps({
            "files": len(files), "primitives": total, "errors": len(errors),
            "findings": [f.as_dict() for f in findings],
        }, indent=2))
        return 1 if errors else 0

    if not files:
        print("No Python files found.")
        return 0

    order = {"error": 0, "warning": 1, "info": 2}
    for finding in sorted(findings, key=lambda f: (order[f.level], f.file, f.line)):
        mark = {"error": "ERROR", "warning": "warn ", "info": "note "}[finding.level]
        where = f"{finding.file}:{finding.line}" if finding.line else finding.file
        print(f"{mark}  {where}  [{finding.rule}]")
        print(f"        {finding.message}")
        if finding.hint:
            print(f"        → {finding.hint}")

    print()
    if not findings:
        print(f"Clean — {total} primitive(s) across {len(files)} file(s).")
    else:
        print(f"{total} primitive(s): {len(errors)} error(s), "
              f"{len(findings) - len(errors)} to look at")

    return 1 if errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
