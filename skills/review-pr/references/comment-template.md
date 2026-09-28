# Comment body template

`scripts/post_review.py` renders this automatically. Use it by hand only if the script is unavailable. Keep the structure exactly — no extra sections, same blank lines (including the blank line between the last `</details>` and the feedback `<sub>` line).

The emoji are intentional: this is user-facing content posted to GitHub.

`````markdown
**Bug:** <1–2 sentences: what is wrong and the user-visible impact>
<sub>Severity: CRITICAL | Confidence: High</sub>
<!-- BUG_PREDICTION -->

<details>
<summary>🔍 <b>Detailed Analysis</b></summary>

<Full explanation: what the code does, why it fails, and the concrete failure scenario — reference actual identifiers, endpoints, and data shapes from the diff.>
</details>

<details>
<summary>💡 <b>Suggested Fix</b></summary>

<Concrete fix. Name the exact lines/changes, e.g. "Change `setRequests(data.requests)` to `setRequests(data.examRequests)`". Include code when helpful.>
</details>

<details>
<summary>🤖 <b>Prompt for AI Agent</b></summary>
<div style='height:6px'></div>

```
Review the code at the location below. A potential bug has been identified by an AI
agent.
Verify if this is a real issue. If it is, propose a fix; if not, explain why it's not
valid.

Location: <repo-relative-path>#L<start>-L<end>

Potential issue: <the detailed analysis text, verbatim, wrapped at ~80 chars>
```
</details>


<sub><i>Did we get this right? :+1: / :-1: to inform future reviews.</i></sub>
<sub>Reference ID: `<7-hex-id>`</sub>
`````

Field rules:

- Severity/Confidence: from the scales in SKILL.md, e.g. `Severity: HIGH | Confidence: Medium`.
- `Location:` repo-relative path + range, e.g. `src/app/api/portal/getRequests/route.js#L61-L68`; single line `#L61`.
- Reference ID: one per comment — `openssl rand -hex 4 | cut -c1-7`.
