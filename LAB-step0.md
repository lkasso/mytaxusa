[Overview](LAB.md) | [Next: Step 1](LAB-step1.md) | [Stuck?](LAB-troubleshooting.md)

# Step 0: Setup and verify (5 min)

Clone the repo. The dependencies, including `claude-agent-sdk`, are already in `pyproject.toml` and `uv.lock`.

Then add your API key to your environment and run the app with:

```bash
uv sync --frozen
export ANTHROPIC_API_KEY=sk-...   # the app does not read .env
uv run python run.py
```

Open http://127.0.0.1:5000/returns.

Use only the fictional samples. Document and return content is sent to the configured model provider.

Three returns are already there to save you time (so you don't have to run or upload anything):

| Return                          | What it is                                                                  |
| ------------------------------- | --------------------------------------------------------------------------- |
| Milo Ledger 2025 (prior year)   | Last year's return. No dependents.                                          |
| Milo Ledger 2026 (clean)        | Everything matches. Must come back `pass`.                                  |
| Milo Ledger 2026 (needs review) | The W-2 was entered wrong and a dependent appeared. Must come back `hold`.  |

1. Open **Milo Ledger 2026 (needs review)**. It opens on the Summary page.
2. Check that the Return review section lists `PRIOR_DEPENDENTS_CHANGED`.
3. Click **Run AI review**. You should see a "no report" error. That is the starter.

**Do not edit the returns and do not apply extracted W-2 values.** The mismatch is the test. If you break a return, stop the server, delete `instance/practice.sqlite3`, restart it and reload.

TIP: After changing Python files, stop the server with Ctrl+C and restart `uv run python run.py`. Changes to the workspace-template Markdown files are copied into the next review automatically.

---

[Overview](LAB.md) | [Next: Step 1](LAB-step1.md) | [Stuck?](LAB-troubleshooting.md)
