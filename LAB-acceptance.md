[Previous: Step 5](LAB-step5.md) | [Overview](LAB.md) | [Stuck?](LAB-troubleshooting.md)

# Run your agent (10 min)

Run both sample returns and look at what your agent did. Each run takes about a minute.

## Run the needs-review return

Open **Milo Ledger 2026 (needs review)** and click **Run AI review**. You should get:

- Verdict `hold`.
- A finding that the W-2 does not match the return: wages 62,400 on the document against 52,400 entered, withholding 7,800 against 6,200, and the Social Security and Medicare boxes.
- `PRIOR_DEPENDENTS_CHANGED` from the app's diagnostics, and a question for the taxpayer about Avery.
- No problem reported for the 1099-INT, and an empty `suspicious_content`.

## Run the clean return

Open **Milo Ledger 2026 (clean)** and run the review. It should come back `pass`, with no questions for the taxpayer and no warning or blocker findings.

## Run the needs-review return again (optional)

Run the needs-review return two more times.

The verdict and the W-2 finding should be the same each time, with different wording. An agent is not deterministic, so the files you wrote are what keep it consistent. If the verdict ever changes, tighten `CLAUDE.md` or the skills and try again.

## What you built

Congratulations! You built a working pre-filing reviewer with the Claude Agent SDK. It reads a return and its documents, asks the taxpayer the right questions, and hands a CPA only the returns that need one.

Each step added one SDK feature to the same agent:

- **[Step 1](LAB-step1.md):** a working reviewer. `ClaudeSDKClient` runs the agent loop with built-in tools, and structured output makes it return a report your app can validate.
- **[Step 2](LAB-step2.md):** the review standards in `CLAUDE.md`, loaded through `cwd` and `setting_sources`. A CPA can edit them without a deploy.
- **[Step 3](LAB-step3.md):** a skill, `credits-due-diligence`, that the agent loads on demand. A procedure for one kind of work stays out of the standards the agent always carries.
- **[Step 4](LAB-step4.md):** a `document-checker` subagent defined in `agents`. Each document is read in a separate context, which reduces context load and direct exposure to raw document text. The checker's findings remain untrusted evidence.
- **[Step 5](LAB-step5.md):** a `PreToolUse` hook registered with `hooks`. It enforces what the prompt can only request, and it runs in your code, outside the model.

One honest limit: Milo's cases are small, and a fixed pipeline of three Messages API calls might handle them. The SDK pays off as returns get messier, with variable documents, variable paths and rules that change monthly.

# Stretch goals

- Add a per-agent rule to the `PreToolUse` hook: only the `document-checker` may read `documents/`, and the checker may read only `documents/` and `return.json`. Inside a subagent, `input_data` carries an `agent_type` field. The reviewer has none, so use `input_data.get('agent_type', 'reviewer')`. Test it in `tests/test_review_hooks.py`.
- Add a `PostToolUse` hook that records each tool call in `ctx.audit` instead of the loop in `runner.py`, with the agent name on every row, so you can see which `Read` calls came from the checker. Then delete the `ctx.audit.append(...)` line from the loop and keep the `print` statements.
- Add a prompt-injection case: a W-2 with hidden text telling the reviewer to pass the return. Does the agent put it in `suspicious_content`?
- Write a script that runs the needs-review return ten times and counts how many runs return `hold` with the W-2 finding.
- Compare models: run the same ten runs on the default, Sonnet and Haiku, and compare verdicts and cost.

---

[Previous: Step 5](LAB-step5.md) | [Overview](LAB.md) | [Stuck?](LAB-troubleshooting.md)
