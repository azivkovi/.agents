#!/usr/bin/env python3
"""Render findings into the bug-prediction comment format and post them as one PR review.

Usage:
    python3 post_review.py --pr <N-or-URL> --findings findings.json [--dry-run]

findings.json: a JSON list of objects with keys
    path, line, start_line (optional), severity, confidence, summary, analysis, fix

Flow:
  1. Resolve owner/repo, head commit, title and URL via `gh pr view`.
  2. Validate each range against `gh pr diff` (RIGHT side, single hunk).
  3. POST one review with all line-anchored comments.
  4. On failure, post each comment individually; if that fails too, post a
     file-level comment (subject_type=file). All of these are resolvable threads.
"""
import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from diff_lines import parse_diff  # noqa: E402

SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
CONFIDENCES = ["High", "Medium", "Low"]

PROMPT_HEADER = (
    "Review the code at the location below. A potential bug has been identified by an AI\n"
    "agent.\n"
    "Verify if this is a real issue. If it is, propose a fix; if not, explain why it's not\n"
    "valid."
)


def gh(args, stdin=None):
    return subprocess.run(["gh", *args], input=stdin, capture_output=True, text=True)


def gh_ok(args):
    r = gh(args)
    if r.returncode != 0:
        sys.exit(f"gh {' '.join(args)} failed:\n{r.stderr}")
    return r.stdout


def location(f):
    start = f.get("start_line")
    if start and start != f["line"]:
        return f"{f['path']}#L{start}-L{f['line']}"
    return f"{f['path']}#L{f['line']}"


def wrap(text, width=80):
    paras = text.strip().split("\n")
    return "\n".join(textwrap.fill(p, width) if p.strip() else "" for p in paras)


def render_body(f, ref_id):
    analysis = f["analysis"].strip()
    prompt = f"{PROMPT_HEADER}\n\nLocation: {location(f)}\n\n{wrap('Potential issue: ' + analysis)}"
    return (
        f"**Bug:** {f['summary'].strip()}\n"
        f"<sub>Severity: {f['severity']} | Confidence: {f['confidence']}</sub>\n"
        "<!-- BUG_PREDICTION -->\n"
        "\n"
        "<details>\n"
        "<summary>🔍 <b>Detailed Analysis</b></summary>\n"
        "\n"
        f"{analysis}\n"
        "</details>\n"
        "\n"
        "<details>\n"
        "<summary>💡 <b>Suggested Fix</b></summary>\n"
        "\n"
        f"{f['fix'].strip()}\n"
        "</details>\n"
        "\n"
        "<details>\n"
        "<summary>🤖 <b>Prompt for AI Agent</b></summary>\n"
        "<div style='height:6px'></div>\n"
        "\n"
        "```\n"
        f"{prompt}\n"
        "```\n"
        "</details>\n"
        "\n"
        "\n"
        "<sub><i>Did we get this right? :+1: / :-1: to inform future reviews.</i></sub>\n"
        f"<sub>Reference ID: `{ref_id}`</sub>"
    )


def validate(f):
    for key in ("path", "line", "severity", "confidence", "summary", "analysis", "fix"):
        if not f.get(key):
            return f"missing '{key}'"
    if f["severity"] not in SEVERITIES:
        return f"severity must be one of {SEVERITIES}"
    if f["confidence"] not in CONFIDENCES:
        return f"confidence must be one of {CONFIDENCES}"
    if "```" in f["analysis"]:
        return "analysis contains a fenced code block (breaks the AI-agent prompt fence); move code to 'fix'"
    return None


def placeable(f, diff_map):
    """True if the whole range is commentable on the RIGHT side within one hunk."""
    lines = diff_map.get(f["path"])
    if not lines:
        return False
    start = f.get("start_line") or f["line"]
    if start > f["line"]:
        return False
    hunks = {lines.get(n) for n in range(start, f["line"] + 1)}
    return None not in hunks and len(hunks) == 1


def line_comment(f, body, commit=None):
    c = {"path": f["path"], "line": f["line"], "side": "RIGHT", "body": body}
    start = f.get("start_line")
    if start and start != f["line"]:
        c["start_line"] = start
        c["start_side"] = "RIGHT"
    if commit:
        c["commit_id"] = commit
    return c


def post_json(endpoint, payload):
    return gh(["api", endpoint, "-X", "POST", "--input", "-"], stdin=json.dumps(payload))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pr", required=True, help="PR number, #N, or URL")
    ap.add_argument("--findings", required=True)
    ap.add_argument("--dry-run", action="store_true", help="print bodies and payload, post nothing")
    args = ap.parse_args()

    pr_ref = args.pr.lstrip("#")
    info = json.loads(gh_ok(["pr", "view", pr_ref, "--json", "number,title,url,headRefOid"]))
    m = re.match(r"https://[^/]+/([^/]+/[^/]+)/pull/(\d+)", info["url"])
    if not m:
        sys.exit(f"Could not parse owner/repo from {info['url']}")
    repo, number, commit = m.group(1), info["number"], info["headRefOid"]
    diff_map = parse_diff(gh_ok(["pr", "diff", pr_ref]))

    with open(args.findings) as fh:
        findings = json.load(fh)

    ready, skipped = [], []
    for f in findings:
        err = validate(f)
        if err:
            skipped.append((f, err))
        elif f["confidence"] == "Low":
            skipped.append((f, "Low confidence — not posted"))
        elif f["severity"] == "LOW":
            skipped.append((f, "LOW severity — not posted"))
        else:
            f["_body"] = render_body(f, secrets.token_hex(4)[:7])
            f["_placeable"] = placeable(f, diff_map)
            ready.append(f)

    order = {s: i for i, s in enumerate(SEVERITIES)}
    ready.sort(key=lambda f: order[f["severity"]])

    for f, why in skipped:
        print(f"SKIPPED {f.get('path')}#L{f.get('line')}: {why}", file=sys.stderr)

    header = f"PR: #{number} — {info['title']} ({info['url']})"
    if not ready:
        print(f"PR Review Complete\n\n{header}\nNo actionable issues found — no comments posted.")
        return

    inline = [f for f in ready if f["_placeable"]]
    payload = {
        "commit_id": commit,
        "event": "COMMENT",
        "comments": [line_comment(f, f["_body"]) for f in inline],
    }

    if args.dry_run:
        for f in ready:
            where = "inline" if f["_placeable"] else "file-level (range not in diff)"
            print(f"===== {location(f)} [{where}] =====\n{f['_body']}\n")
        print("===== review payload =====")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    endpoint_comments = f"repos/{repo}/pulls/{number}/comments"
    results = {}

    if inline:
        r = post_json(f"repos/{repo}/pulls/{number}/reviews", payload)
        if r.returncode == 0:
            for f in inline:
                results[id(f)] = "inline"
        else:
            print(f"Review POST failed, retrying individually:\n{r.stderr.strip()}", file=sys.stderr)
            for f in inline:
                r1 = post_json(endpoint_comments, line_comment(f, f["_body"], commit))
                if r1.returncode == 0:
                    results[id(f)] = "inline"
                else:
                    f["_placeable"] = False  # fall through to file-level

    for f in ready:
        if f["_placeable"]:
            continue
        r2 = post_json(endpoint_comments, {
            "body": f["_body"], "commit_id": commit,
            "path": f["path"], "subject_type": "file",
        })
        results[id(f)] = "file-level" if r2.returncode == 0 else f"FAILED: {r2.stderr.strip()}"

    posted = [f for f in ready if not results.get(id(f), "").startswith("FAILED")]
    print(f"PR Review Complete\n\n{header}\nComments posted: {len(posted)}\n")
    for i, f in enumerate(ready, 1):
        status = results.get(id(f), "unknown")
        note = "" if status == "inline" else f" ({status})"
        short = f.get("title") or f["summary"].strip().split(". ")[0].rstrip(".")
        print(f"{i}. [{f['severity']}] {location(f)} — {short}{note}")


if __name__ == "__main__":
    main()
