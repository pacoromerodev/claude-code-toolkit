#!/usr/bin/env python3
"""PreToolUse guard: block writing a bank account, a card number or a Spanish
national ID into a file.

Reads the hook payload on stdin. Exit 2 blocks the tool call and hands stderr
back to Claude as feedback; any other exit lets the call through, so a bug in
this guard never breaks a session.

A pattern alone would block every sixteen-digit number. Each value found is
checked the way its issuer checks it, so what is blocked is a value that would
be accepted as real:

  IBAN      the country's registered length, and the ISO 13616 mod-97 check
  card      13 to 19 digits, a known scheme prefix, and the Luhn check
  DNI/NIE   eight digits (or X/Y/Z and seven) and the matching control letter

The published test values (4111 1111 1111 1111, GB82 WEST 1234 5698 7654 32,
12345678Z and the like) pass: they exist to be written into tests. Projects
can allow more in `.claude/pii-guard-allow`, one regular expression per line,
matched against the value with its spaces removed. That file is itself
blocked: an exception is the user's decision, not the agent's.

Covers Write, Edit, MultiEdit and NotebookEdit. A shell command is not read.
"""
import json
import os
import re
import sys
from pathlib import Path

ALLOW_FILE = re.compile(r"(^|[/\\])\.claude[/\\]pii-guard-allow$")

# ISO 13616 registry lengths. A country that is not here is not checked: an
# unknown prefix is more likely a product code than an account.
IBAN_LENGTH = {
    "AD": 24, "AE": 23, "AL": 28, "AT": 20, "AZ": 28, "BA": 20, "BE": 16,
    "BG": 22, "BH": 22, "BR": 29, "BY": 28, "CH": 21, "CR": 22, "CY": 28,
    "CZ": 24, "DE": 22, "DK": 18, "DO": 28, "EE": 20, "EG": 29, "ES": 24,
    "FI": 18, "FO": 18, "FR": 27, "GB": 22, "GE": 22, "GI": 23, "GL": 18,
    "GR": 27, "GT": 28, "HR": 21, "HU": 28, "IE": 22, "IL": 23, "IQ": 23,
    "IS": 26, "IT": 27, "JO": 30, "KW": 30, "KZ": 20, "LB": 28, "LC": 32,
    "LI": 21, "LT": 20, "LU": 20, "LV": 21, "MC": 27, "MD": 24, "ME": 22,
    "MK": 19, "MR": 27, "MT": 31, "MU": 30, "NL": 18, "NO": 15, "PK": 24,
    "PL": 28, "PS": 29, "PT": 25, "QA": 29, "RO": 24, "RS": 22, "SA": 24,
    "SC": 31, "SE": 24, "SI": 19, "SK": 24, "SM": 27, "ST": 25, "SV": 28,
    "TL": 23, "TN": 24, "TR": 26, "UA": 29, "VA": 22, "VG": 24, "XK": 20,
}

# Values published as examples, by the IBAN registry, card schemes and payment
# providers, and the DNI in every Spanish form template. Real by checksum,
# owned by nobody.
PUBLISHED_EXAMPLES = {
    "GB82WEST12345698765432", "GB29NWBK60161331926819",
    "DE89370400440532013000", "NL91ABNA0417164300",
    "FR1420041010050500013M02606", "ES9121000418450200051332",
    "4111111111111111", "4242424242424242", "4012888888881881",
    "4000056655665556", "5555555555554444", "5105105105105100",
    "5200828282828210", "378282246310005", "371449635398431",
    "6011111111111117", "6011000990139424", "3530111333300000",
    "30569309025904",
    "12345678Z",
}

IBAN = re.compile(r"(?<![A-Z0-9])([A-Z]{2})(\d{2})((?:[ ]?[A-Z0-9]){10,32})")
CARD = re.compile(r"(?<![\d.-])(\d(?:[ -]?\d){12,18})(?![\d-]|\.\d)")
DNI = re.compile(r"(?<![A-Za-z0-9])(\d{8})-?([A-Za-z])(?![A-Za-z0-9])")
NIE = re.compile(r"(?<![A-Za-z0-9])([XYZxyz])-?(\d{7})-?([A-Za-z])(?![A-Za-z0-9])")

DNI_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"

# Scheme prefixes and lengths. A Luhn-valid number outside these is an
# identifier that happens to pass, which is one in ten of them.
CARD_SCHEMES = [
    ("Visa", re.compile(r"^4"), {13, 16, 19}),
    ("Mastercard", re.compile(r"^(5[1-5]|222[1-9]|22[3-9]\d|2[3-6]\d\d|27[01]\d|2720)"), {16}),
    ("American Express", re.compile(r"^3[47]"), {15}),
    ("Diners Club", re.compile(r"^3(0[0-5]|[689])"), {14, 16}),
    ("Discover", re.compile(r"^(6011|65|64[4-9])"), {16, 19}),
    ("JCB", re.compile(r"^35(2[89]|[3-8]\d)"), {16, 17, 18, 19}),
    ("UnionPay", re.compile(r"^62"), {16, 17, 18, 19}),
]


def iban_valid(value):
    rearranged = value[4:] + value[:4]
    digits = "".join(str(int(ch, 36)) for ch in rearranged)
    return int(digits) % 97 == 1


def luhn_valid(digits):
    total = 0
    for index, ch in enumerate(reversed(digits)):
        n = int(ch)
        if index % 2:
            n = n * 2 - 9 if n > 4 else n * 2
        total += n
    return total % 10 == 0


def find_ibans(text):
    for match in IBAN.finditer(text):
        country = match.group(1)
        length = IBAN_LENGTH.get(country)
        if length is None:
            continue
        compact = (match.group(1) + match.group(2) + match.group(3)).replace(" ", "")
        if len(compact) < length:
            continue
        value = compact[:length]
        if value.isalnum() and iban_valid(value):
            yield "IBAN", value, match.start()


def find_cards(text):
    for match in CARD.finditer(text):
        raw = match.group(1)
        digits = re.sub(r"[ -]", "", raw)
        # A separator used, it is used the same way throughout: "4111 1111"
        # is a card written out, "4111-1111 11" is two numbers side by side.
        if " " in raw and "-" in raw:
            continue
        if len(set(digits)) == 1 or not luhn_valid(digits):
            continue
        for scheme, prefix, lengths in CARD_SCHEMES:
            if prefix.match(digits) and len(digits) in lengths:
                yield f"{scheme} card number", digits, match.start()
                break


def find_national_ids(text):
    for match in DNI.finditer(text):
        number, letter = match.group(1), match.group(2).upper()
        if DNI_LETTERS[int(number) % 23] == letter:
            yield "DNI", number + letter, match.start()
    for match in NIE.finditer(text):
        prefix, number, letter = match.group(1).upper(), match.group(2), match.group(3).upper()
        if DNI_LETTERS[int(str("XYZ".index(prefix)) + number) % 23] == letter:
            yield "NIE", prefix + number + letter, match.start()


def findings(text):
    yield from find_ibans(text)
    yield from find_cards(text)
    yield from find_national_ids(text)


def text_of(tool_input):
    """Everything this call would put on disk."""
    parts = []
    for key in ("content", "new_string", "new_source"):
        value = tool_input.get(key)
        if isinstance(value, str):
            parts.append(value)
    edits = tool_input.get("edits")
    if isinstance(edits, list):
        for edit in edits:
            if isinstance(edit, dict) and isinstance(edit.get("new_string"), str):
                parts.append(edit["new_string"])
    return "\n".join(parts)


def working_directory(payload):
    for candidate in (payload.get("cwd"), os.environ.get("CLAUDE_PROJECT_DIR")):
        if candidate and Path(candidate).is_dir():
            return Path(candidate).resolve()
    return Path.cwd().resolve()


def project_allowlist(root):
    try:
        lines = (Path(root) / ".claude" / "pii-guard-allow").read_text(encoding="utf-8").splitlines()
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


def masked(value):
    return value[:4] + "…" + value[-4:] if len(value) > 10 else "…" + value[-4:]


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0

    for key in ("file_path", "notebook_path"):
        path = tool_input.get(key)
        if isinstance(path, str) and ALLOW_FILE.search(path):
            print(
                f"Blocked by guard_pii: {path} is the guard's exception list. "
                "Adding an exception is the user's decision.\n"
                "Do not write it another way. If a value really must be "
                "allowed, tell the user which one and why, and ask them to add "
                "it themselves.",
                file=sys.stderr,
            )
            return 2

    body = text_of(tool_input)
    if not body:
        return 0
    allowlist = project_allowlist(working_directory(payload))

    for label, value, offset in findings(body):
        if value in PUBLISHED_EXAMPLES:
            continue
        if any(rule.search(value) for rule in allowlist):
            continue
        line = body[:offset].count("\n") + 1
        target = tool_input.get("file_path") or tool_input.get("notebook_path") or "the file"
        print(
            f"Blocked by guard_pii: line {line} of the text for {target} holds "
            f"{'an' if label[0] in 'AEIOU' else 'a'} {label} ({masked(value)}) "
            "that passes its issuer's check, so it "
            "could belong to a real person. Nothing was written.\n"
            "Do not retry with the value split, encoded or moved to another "
            "file. Instead:\n"
            "- Test data: use a published test value (card 4111 1111 1111 1111, "
            "IBAN GB82 WEST 1234 5698 7654 32 or ES91 2100 0418 4502 0005 1332, "
            "DNI 12345678Z), or one that fails its check digit on purpose.\n"
            "- Real data the code needs: read it at runtime from where it is "
            "held, never from source or fixtures.\n"
            "- If the user says this exact value is safe, ask them to add it to "
            ".claude/pii-guard-allow themselves.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # fail open: a crash must never block the session
