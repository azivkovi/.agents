---
name: review-pr
description: Review a GitHub pull request for concrete bugs and post actionable inline comments when requested. Use when asked to review a PR with comments or when explicitly invoked as $review-pr.
---

# Review a pull request

Find defects introduced by a PR and explain them in resolvable inline threads. Explicit use of `$review-pr` or a request to leave review comments authorizes posting qualifying findings. If the user asks for a read-only review, report findings locally and do not post.

Accept a PR number, URL, or `#123`. With no target, use the PR for the current branch. Do not post if the target cannot be identified unambiguously.

## Resolve and inspect

Use `gh pr view` to obtain the PR number, URL, title, body, head SHA, and changed files. Derive `OWNER/REPO` from the **resolved PR URL**, not from the current directory. Pass `-R OWNER/REPO` to subsequent `gh pr` calls, and use that same owner and repo for `gh api` calls. Fetch the complete diff with `gh pr diff -R OWNER/REPO <number>` and check it against the changed-file list. If the diff is incomplete or unavailable, disclose that limit; do not claim a complete review.

Review code at the PR head SHA. A local checkout may be on another branch or commit: verify its SHA before using it, or fetch the head into an isolated checkout/worktree. Read relevant callers, consumers, tests, API contracts, and configuration when they determine whether a suspected bug is real. If Sentry telemetry is available and relevant, use it as additional evidence; never imply telemetry was checked when it was not.

Check existing PR review comments with `gh api "repos/OWNER/REPO/pulls/<number>/comments" --paginate`. Before posting, compare each finding with existing comments on the same code path and failure mode, including comments from other reviewers. Skip duplicates and issues already fixed by a later PR commit.

## Select findings

Post only when all of these are true:

- The change causes a concrete runtime, security, data, performance, compatibility, or API-contract failure.
- The failure scenario and its impact are specific and supported by the code path.
- The finding can be anchored to an appropriate line in the PR diff and has a practical fix.

Check for failures such as exceptions, incorrect data shapes, access-control gaps, unbounded work or N+1 queries, and breaking changes to callers. Do not post style or naming advice, generic test requests, or speculative possibilities. If no finding qualifies, post nothing; do not leave an approval or “LGTM” comment merely to record the review.

Use severity to describe **impact**, not the presence of a crash:

| Severity | Use for |
| --- | --- |
| CRITICAL | Widespread outage, data loss, or serious security exposure |
| HIGH | A broken feature or severe failure with a narrower scope |
| MEDIUM | A reproducible edge case or meaningful degraded behavior |
| LOW | Minor impact; normally do not post |

Confidence is **High** when the relevant code path verifies the claim, **Medium** when strong evidence remains subject to one stated, bounded assumption, and **Low** when evidence is insufficient. Do not post Low-confidence findings. Do not present a Medium-confidence possibility as a proven bug.

## Write comments

Keep each thread short enough to scan. State the bug and impact first, then the evidence and a concrete fix. For example:

```markdown
**Bug:** This reads `data.requests`, but the endpoint returns `examRequests`, so the page fails when it renders the response.

**Evidence:** `getRequests` returns `{ examRequests }`; this component passes `data.requests` to `setRequests` and later calls `.map` on it.

**Fix:** Pass `data.examRequests` to `setRequests`.

<sub>Severity: HIGH · Confidence: High</sub>
```

Use actual identifiers and behavior from the PR; do not copy the example as a finding. State any bounded assumption behind Medium confidence. Avoid Sentry or Seer markers, feedback claims, and reference IDs unless this review is actually being posted by that system. An agent-facing verification prompt is optional only when the user or repository workflow calls for one.

## Post and report

Anchor to the smallest relevant changed line or range. For added or changed code, use new-file line numbers with `side: "RIGHT"`; use `side: "LEFT"` for a deletion. A multiline comment also needs `start_line` and `start_side`, with `line` as the final line. Validate path, side, and line numbers against the diff before posting. Do not replace an invalid line anchor with a file-level comment automatically. See [GitHub's review comment parameters](https://docs.github.com/en/rest/pulls/comments).

Prefer one review containing all qualifying inline comments. Build JSON with `jq` so comment text is escaped correctly. For `POST repos/OWNER/REPO/pulls/<number>/reviews`, include the reviewed `commit_id`, `event: "COMMENT"`, a short required review `body` (for example, `"Actionable findings are inline."`), and a `comments` array whose entries contain `path`, `line`, `side`, `body`, plus `start_line` and `start_side` for ranges. Do not post findings in the top-level review body or with `gh pr comment`. See [GitHub's create-review parameters](https://docs.github.com/en/rest/pulls/reviews).

Immediately before posting, recheck the PR head SHA. If it changed, refresh the diff and revalidate findings and anchors. On a `422` response, inspect the returned error: it may indicate invalid placement or another validation/rate-limit problem. Retry only after correcting a confirmed cause and rechecking for comments already posted; otherwise stop and report the unposted findings. Do not silently switch to individual or file-level posts.

Report the PR URL, reviewed head SHA, concise findings with file/line links, and how many comments were posted, skipped as duplicates, or left unposted. For a read-only review, label all findings unposted. If there are no actionable issues, say so without implying the review proves the PR bug-free.
