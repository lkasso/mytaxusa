# Lab: build a tax pre-filing reviewer with the Claude Agent SDK

**Time:** 60 minutes.
**Language:** Python.
**You need:** Python 3.11+, [uv](https://docs.astral.sh/uv/), an `ANTHROPIC_API_KEY` and a basic understanding of LLM APIs.

## The scenario

Fake, Inc. owns MyTaxUSA, a tax app. The CEO, Andrew Smith, wants most simple returns cleared without a CPA touching them, so CPAs only see the exceptions. Before a taxpayer files, an agent does what a preparer's self-review does: it ties the documents to the return, compares against last year, checks the credits, and asks the taxpayer about anything that does not add up.

You will build this fully functional agent in the next hour.

The agent ends with a verdict:

| Verdict | Meaning                                    |
| ------- | ------------------------------------------ |
| `pass`  | Clear. No CPA needed.                      |
| `warn`  | The taxpayer must answer a question first. |
| `hold`  | A CPA must look.                           |

To build this agent, Andrew Smith has given you sample data for a taxpayer named Milo Ledger (Single, Los Angeles). His 2026 return has two problems the agent should find: the W-2 was entered wrong, and a dependent appeared that was not on his 2025 return.

## What you build

You will build this agent with the Claude Agent SDK instead of writing your own code around the model:

| Step              | You add                        | SDK feature                                                      |
| ----------------- | ------------------------------ | ---------------------------------------------------------------- |
| [1](LAB-step1.md) | A working reviewer             | `ClaudeSDKClient`, built-in tools, structured output             |
| [2](LAB-step2.md) | The review standards as a file | `CLAUDE.md` via `cwd` and `setting_sources`                      |
| [3](LAB-step3.md) | A credits skill                | Skills in `.claude/skills/<name>/SKILL.md`, `skills`, `Skill`    |
| [4](LAB-step4.md) | A document-checker             | Subagents via `agents` and the `Agent` tool                      |
| [5](LAB-step5.md) | Guardrails in code             | A `PreToolUse` hook via `hooks`                                  |

This lab breaks down into the following steps. Each one has its own page, with links to the previous and next step:

| Step                                              | Minutes |
| ------------------------------------------------- | ------- |
| [0 Setup and verify](LAB-step0.md)                | 5       |
| [1 First working reviewer](LAB-step1.md)          | 12      |
| [2 Project instructions](LAB-step2.md)            | 7       |
| [3 Skill](LAB-step3.md)                           | 8       |
| [4 Subagent](LAB-step4.md)                        | 8       |
| [5 Hooks and denial test](LAB-step5.md)           | 10      |
| [Run your agent](LAB-acceptance.md)               | 10      |

This lab uses the Claude Agent SDK instead of the plain Messages API (or Client SDK). With the API, you would have to write the tool loop, file access, context handling and permission checks yourself. Here the review rules live in markdown files you can edit without a deploy, each document is read in its own context, and a hook decides what the agent may touch, outside the model.

## What is already built

- The Flask app: a mock of the MyTaxUSA website where a user enters personal information, income (W-2s, 1099s) and payments to produce a practice Form 1040. The README has the details.
- The Summary page, where the user downloads the 1040 and sees the AI agent review.
- Three sample returns, loaded for you. [Step 0](LAB-step0.md) walks through them.
- `workspace.py`. For each review, it builds a temporary folder the agent works in:

    ```text
    return.json        this year's return
    prior.json         last year's return (or null)
    diagnostics.json   the app's own deterministic findings
    manifest.json      the list of attached documents
    documents/*.txt    text of each attached document
    .claude/skills/    two provided skills: tie-out, prior-year-variance
    ```

NOTE: Documents are text, not PDFs, on purpose: the built-in Read tool on a large PDF overflows the SDK's 1 MiB message buffer.

All of your code goes in `app/services/review_agent/`. That folder is the Flask app's service layer: the code behind the routes that does the real work, such as calculation rules, diagnostics and document extraction. When a user clicks **Run AI review**, `POST /review` in `app/routes/review.py` builds a snapshot of the return and calls `run_review(ctx)` in `runner.py`. It saves what comes back and redirects to the Summary page. The route already handles the web side, so your agent only takes a `ReviewContext` and returns a `ReviewOutcome`. You never touch templates, routes or the database in this lab.

The starter `runner.py` has a `run_review(ctx)` that returns `None`.

Start with [Step 0: Setup and verify](LAB-step0.md). If you get stuck at any point, see [Troubleshooting and recovery](LAB-troubleshooting.md).
