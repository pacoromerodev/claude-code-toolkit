#!/usr/bin/env python3
"""No sentence in this repository is a sentence from the course notes.

The concepts are free to reuse. The wording is not, and a paraphrase written
from memory drifts towards the original without anyone noticing. This compares
every short run of words in `plugins/**` against the same runs taken from the
notes, and reports the ones that match.

The notes are not in this repository and are not public, so what is committed
is `data/course-shingles.txt`: truncated SHA-256 hashes, one per line, no
text. It is regenerated deliberately, from a local checkout of the academy
repository, and from two sources in it:

    python3 .github/scripts/check_course_wording.py --update \
        --notes ../anthropic-academy-es/web/src \
        --notes ../anthropic-academy-es/cursos/_bundles

`web/src` is the Spanish notes. `cursos/` holds the lessons themselves, in
the original English, and is the source that matters: a sentence lifted from
a course is lifted from there. `--notes` may be given more than once, and a
directory is read recursively.

What it can and cannot see:

  - it sees English reused verbatim, from the lessons or from the notes
  - it does not see a paraphrase, and it cannot see a Spanish passage rendered
    into English. That one stays a manual read before publication

A run counts as prose only if it holds at least two common English words and
three words that are not, so a shared command line, import or stock phrase is
not mistaken for shared writing. The window is five words, and both numbers
were calibrated against the one passage the audit found: eight words missed it
entirely, five alone also flagged "or when the user asks to" in six skill
descriptions, and requiring three content words leaves the real one alone.

Usage: check_course_wording.py [--enforce] [--fingerprints <file>] [root]
       check_course_wording.py --update --notes <dir> [--notes <dir> ...]
                               [--fingerprints <file>]
"""
import hashlib
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(__file__).resolve().parent / "data" / "course-shingles.txt"

WINDOW = 5
MIN_CONTENT = 3
DIGEST = 12
WORD = re.compile(r"[a-z0-9']+")

# Two of these in a run is what separates a sentence from a command line. A
# Spanish sentence holds none, which is the honest limit of this check and is
# stated in the report.
ENGLISH = {
    "the", "a", "an", "of", "to", "and", "or", "is", "are", "was", "were",
    "it", "its", "that", "this", "these", "those", "you", "your", "for",
    "in", "on", "with", "without", "not", "be", "been", "as", "at", "by",
    "from", "but", "so", "than", "then", "when", "what", "which", "who",
    "how", "why", "if", "into", "over", "about", "there", "their", "they",
    "we", "our", "can", "will", "would", "should", "does", "do", "did",
}


def shingles(text):
    """Every run of WINDOW words that reads like prose, and where it starts."""
    words, lines = [], []
    for number, line in enumerate(text.splitlines(), start=1):
        for word in WORD.findall(line.lower()):
            words.append(word)
            lines.append(number)

    for index in range(len(words) - WINDOW + 1):
        run = words[index:index + WINDOW]
        if sum(1 for word in run if word in ENGLISH) < 2:
            continue
        if sum(1 for word in run if word not in ENGLISH and len(word) >= 3) < MIN_CONTENT:
            continue
        digest = hashlib.sha256(" ".join(run).encode("utf-8")).hexdigest()[:DIGEST]
        yield digest, lines[index], " ".join(run)


def load_fingerprints(data):
    if not data.is_file():
        return None
    return {
        line.strip()
        for line in data.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def update(notes_dirs, data):
    notes = []
    for notes_dir in notes_dirs:
        found = sorted(Path(notes_dir).glob("**/*.md"))
        if not found:
            print(f"No .md files in {notes_dir}")
            return 1
        notes.extend(found)

    digests = set()
    for note in notes:
        for digest, _, _ in shingles(note.read_text(encoding="utf-8")):
            digests.add(digest)

    data.parent.mkdir(parents=True, exist_ok=True)
    data.write_text(
        f"# Truncated SHA-256 of every {WINDOW}-word run in the course notes.\n"
        "# No text: a hash cannot be read back into the sentence it came from.\n"
        f"# {len(notes)} note(s), {len(digests)} run(s), written {date.today()}.\n"
        "# Regenerate: check_course_wording.py --update --notes <dir> [--notes <dir> ...]\n"
        + "".join(f"{digest}\n" for digest in sorted(digests)),
        encoding="utf-8",
    )
    print(f"Wrote {len(digests)} fingerprint(s) from {len(notes)} note(s) to "
          f"{data}")
    return 0


def options(argv, flag):
    """Every value given for a flag that may repeat."""
    return [argv[index + 1] for index, arg in enumerate(argv[:-1])
            if arg == flag]


def option(argv, flag, fallback=None):
    try:
        return argv[argv.index(flag) + 1]
    except (ValueError, IndexError):
        return fallback


def main(argv):
    data = Path(option(argv, "--fingerprints", DATA))

    if "--update" in argv:
        notes = options(argv, "--notes")
        if not notes:
            print("--update needs --notes <directory of course notes>")
            return 1
        return update(notes, data)

    enforce = "--enforce" in argv
    skip = {"--notes", "--fingerprints"}
    rest = [a for index, a in enumerate(argv[1:], start=1)
            if not a.startswith("--") and argv[index - 1] not in skip]
    root = Path(rest[0]).resolve() if rest else ROOT

    fingerprints = load_fingerprints(data)
    if fingerprints is None:
        print(f"No fingerprint file at {data}. Generate it with --update.")
        return 1

    hits = []
    scanned = 0
    for path in sorted(root.glob("plugins/**/*.md")):
        scanned += 1
        for digest, line, run in shingles(path.read_text(encoding="utf-8")):
            if digest in fingerprints:
                hits.append((path.relative_to(root).as_posix(), line, run))

    for path, line, run in hits:
        print(f"{path}:{line}: {WINDOW} words that also read this way in the "
              f"notes: {run}")

    print()
    if not hits:
        print(f"OK — {scanned} file(s), no run of {WINDOW} words matches the "
              f"notes ({len(fingerprints)} fingerprints)")
        print("This cannot see a paraphrase, or a Spanish passage rendered "
              "into English. Those stay a manual read.")
        return 0

    print(f"{len(hits)} match(es) in {scanned} file(s). Reword them: the "
          f"concept is yours to reuse, the sentence is not.")
    return 1 if enforce else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
