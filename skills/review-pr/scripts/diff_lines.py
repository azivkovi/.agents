#!/usr/bin/env python3
"""List the RIGHT-side (new-file) line numbers that can take inline PR comments.

Usage:
    gh pr diff 123 | python3 diff_lines.py [path ...]

Prints, per file, the commentable line ranges grouped by hunk. A multi-line
comment range must fall inside a single hunk.
"""
import re
import sys

HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


def parse_diff(text):
    """Return {path: {line_number: hunk_index}} for RIGHT-side commentable lines."""
    files = {}
    path = None
    hunk = -1
    right = 0
    in_hunk = False
    for raw in text.splitlines():
        if raw.startswith("diff --git "):
            path, in_hunk = None, False
            continue
        if not in_hunk and raw.startswith("+++ "):
            target = raw[4:].strip()
            path = None if target == "/dev/null" else re.sub(r"^b/", "", target)
            if path is not None:
                files.setdefault(path, {})
            continue
        m = HUNK_RE.match(raw)
        if m:
            right = int(m.group(1))
            hunk += 1
            in_hunk = True
            continue
        if not in_hunk or path is None:
            continue
        if raw.startswith("+") or raw.startswith(" ") or raw == "":
            files[path][right] = hunk
            right += 1
        elif raw.startswith("-") or raw.startswith("\\"):
            continue
        else:  # header lines of the next file (index, ---, etc.)
            in_hunk = False
    return files


def ranges(lines_to_hunk):
    """Collapse {line: hunk} into [(start, end), ...] contiguous within a hunk."""
    out = []
    for ln in sorted(lines_to_hunk):
        h = lines_to_hunk[ln]
        if out and out[-1][1] == ln - 1 and out[-1][2] == h:
            out[-1][1] = ln
        else:
            out.append([ln, ln, h])
    return [(s, e) for s, e, _ in out]


def main():
    files = parse_diff(sys.stdin.read())
    wanted = sys.argv[1:]
    for path in sorted(files):
        if wanted and path not in wanted:
            continue
        spans = ", ".join(f"L{s}-L{e}" if s != e else f"L{s}" for s, e in ranges(files[path]))
        print(f"{path}: {spans or '(no commentable lines)'}")


if __name__ == "__main__":
    main()
