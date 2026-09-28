---
name: pr-review
description: Review a GitHub pull request and post actionable inline review comments in a structured bug-prediction format (Bug summary, severity/confidence, collapsible analysis, suggested fix, and a verification prompt for an AI agent). Use this skill whenever the user asks to review a PR, check a pull request for bugs, "look at PR #123", review the current branch's PR, or leave review comments on GitHub — even if they only paste a PR URL or number without saying "review".
---

# PR Review

Review a pull request and leave **actionable inline comments** as resolvable review threads, using one fixed comment format.

**Input:** a PR number, `#123`, or a PR URL taken from the user's request. If none is given, review the PR of the current branch.

**Requires:** `gh` (authenticated), `python3`, run from inside the repo checkout.

## 1. Resolve the PR and gather context

```bash
# No PR given — find the PR for the current branch
gh pr view --json number,title,body,headRefOid,baseRefName,author,url

# PR given (number or URL)
gh pr view <N-or-URL> --json number,title,body,headRefOid,baseRefName,author,url

gh pr diff <N-or-URL>                        # full diff
gh pr view <N-or-URL> --json files           # changed files
```

Run these in parallel where possible. Use the PR `url` as the source of truth for owner/repo — the checkout's default remote may differ (forks).

## 2. Review the diff

Read the FULL diff, not a summary. When a finding depends on code outside the diff (callers, consumers, API response shapes, types), open those files in the repo and verify — that is what separates High from Medium confidence.

**Post a finding only when ALL of these hold:**

- It is a real bug, logic error, data/API mismatch, security issue, race condition, or breaking change
- It points to specific lines in the diff
- There is a concrete failure scenario
- There is a concrete fix

**Do not comment on:** style, naming, formatting, missing tests, "consider…" suggestions, or anything speculative. Noise trains authors to ignore the bot, so an empty review is a good outcome when the PR is clean. Never post "LGTM".

| Severity | Meaning |
|---|---|
| CRITICAL | Crashes, data loss, security holes, broken prod behavior |
| HIGH | A feature is broken or returns wrong data |
| MEDIUM | Edge case or degraded behavior |
| LOW | Minor — not posted |

Confidence: **High** = verified by reading the actual code paths. **Medium** = strong evidence, one unverified assumption. **Low** = do not post.

### Line placement

Inline comments can only anchor to lines inside a diff hunk on the RIGHT side (new-file numbering — added `+` lines and unchanged context lines). A range must sit within a single hunk. To see exactly which lines are commentable:

```bash
gh pr diff <N> | python3 scripts/diff_lines.py            # all files
gh pr diff <N> | python3 scripts/diff_lines.py src/foo.ts # one file
```

## 3. Write the findings file

Put every finding in `/tmp/pr-findings.json`:

```json
[
  {
    "path": "src/app/api/portal/getRequests/route.js",
    "start_line": 61,
    "line": 68,
    "title": "response key mismatch crashes exam-requests page",
    "severity": "CRITICAL",
    "confidence": "High",
    "summary": "The route returns `examRequests` but the page reads `data.requests`, so the exam-requests page crashes on load.",
    "analysis": "Full explanation: what the code does, why it fails, the concrete failure scenario. Reference real identifiers, endpoints and data shapes from the diff.",
    "fix": "Concrete fix naming the exact change, e.g. change `setRequests(data.requests)` to `setRequests(data.examRequests)`. Code blocks are fine here."
  }
]
```

- `title`: short one-liner used in the final report.
- `summary`: 1–2 sentences — what is wrong and the user-visible impact.
- `line` is the LAST line of the range; `start_line` the first. Omit `start_line` for a single line.
- `analysis` is copied verbatim into the AI-agent prompt, which sits inside a code fence — so keep it prose with inline `code` only. Put fenced code blocks in `fix`.

## 4. Post the review

```bash
python3 scripts/post_review.py --pr <N-or-URL> --findings /tmp/pr-findings.json --dry-run  # inspect first
python3 scripts/post_review.py --pr <N-or-URL> --findings /tmp/pr-findings.json
```

The script renders each comment body in the exact format from `references/comment-template.md` (with a fresh 7-hex Reference ID), validates every line range against the diff, and posts all comments as ONE review (single notification, each comment a resolvable thread). If the review is rejected with `422`, it retries each comment individually, and falls back to a file-level comment (`subject_type: file`, still resolvable) for any that can't be placed on a line. It refuses Low-confidence findings and skips LOW severity.

Never post findings via `gh pr comment` or as a top-level review body — those can't be resolved.

If the script can't be used, build the bodies by hand from `references/comment-template.md` and post with `gh api repos/<owner>/<repo>/pulls/<N>/reviews -X POST --input <payload.json>` (`event: "COMMENT"`, `side: "RIGHT"`, `start_side: "RIGHT"` for ranges).

## 5. Report

The script prints this; relay it to the user:

```
PR Review Complete

PR: #123 — <title> (<url>)
Comments posted: 3

1. [CRITICAL] src/app/api/portal/getRequests/route.js#L61-L68 — response key mismatch crashes exam-requests page
2. [HIGH] src/lib/auth.js#L34 — token expiry check uses wrong unit
3. [MEDIUM] src/components/Table.jsx#L102 — unguarded .map on possibly undefined prop
```

If there are zero actionable findings, post nothing and report: "No actionable issues found — no comments posted."
