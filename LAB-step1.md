[Previous: Step 0](LAB-step0.md) | [Overview](LAB.md) | [Next: Step 2](LAB-step2.md) | [Stuck?](LAB-troubleshooting.md)

# Step 1: A reviewer in a workspace (12 min)

**Edit:** `runner.py` only. You will build `run_review()` piece by piece.

Before you start, read `app/services/review_agent/schema.py`. `REPORT_EXAMPLE` at the top shows the report the Summary page expects.

## 1a: Start an agent in the workspace

You do not write an agent loop. The SDK runs it: the agent decides to call a tool, the SDK runs the tool and hands back the result, and this repeats until the agent is done. Your code sends one prompt and listens to the stream of messages.

`workspace.py` already builds the review folder for you. Open it with `review_workspace(ctx)` and point the agent at it. For now, you will just print what the agent says and does.

The options are the controlled configuration for every run, including this first one. Without them, the agent would inherit your personal Claude settings, MCP servers and memory, and could use a different model from the one this lab was tested on. 1b and 1c explain each option.

**1.** Add these imports at the top of `runner.py`, above the dataclasses. `run_review` needs `review_workspace` straight away. The rest are used in 1e and 1f.

```python
import json

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, ResultMessage, TextBlock, ToolUseBlock

from .schema import REPORT_JSON_SCHEMA, validate_report
from .workspace import review_workspace
```

**2.** Replace the body of `run_review` (keep the `async def` line and the dataclasses):

```python
async def run_review(ctx: ReviewContext) -> ReviewOutcome | None:
    # workspace.py builds a temporary folder with this return's data and documents,
    # and deletes it when the `with` block ends.
    with review_workspace(ctx) as workspace:
        options = ClaudeAgentOptions(
            cwd=str(workspace),                            # the agent works inside the review folder
            model='claude-opus-5-5',                       # the model this lab was tested on
            tools=['Read'],                                # the only built-in tool that exists
            allowed_tools=['Read'],                        # pre-approve Read so it runs without asking
            permission_mode='dontAsk',                     # deny anything not pre-approved instead of prompting
            setting_sources=[],                            # no CLAUDE.md or settings files from disk, for now
            mcp_servers={}, strict_mcp_config=True,        # no MCP servers from your machine
            env={'CLAUDE_CODE_DISABLE_AUTO_MEMORY': '1'},  # no auto memory
            max_turns=30,                                  # safety limits, explained in 1c
            max_budget_usd=1.00,
        )
        # ClaudeSDKClient starts the agent and keeps one conversation open until the block ends.
        async with ClaudeSDKClient(options=options) as client:
            # 1. Hand the agent its task. This returns immediately. It does not return an answer.
            await client.query('Read manifest.json and tell me which documents are attached to this return.')

            # 2. Listen. The agent loop runs behind the scenes: Claude thinks, asks to use a tool,
            #    the SDK runs the tool and gives Claude the result, and Claude thinks again.
            #    Each step arrives here as a message. The stream ends after the final ResultMessage.
            async for message in client.receive_response():

                # 3. An AssistantMessage is something Claude said or did. It holds a list of blocks.
                #    (Other message types, such as tool results, are ignored for now.)
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):        # plain text from Claude
                            print('AGENT:', block.text)
                        elif isinstance(block, ToolUseBlock):   # Claude asked to run a tool
                            print('TOOL:', block.name, block.input)
    return None  # still no report. That comes in 1e and 1f.
```

For a review of this return, the stream looks roughly like this: an `AssistantMessage` with a `Read` tool call, the tool result, an `AssistantMessage` with text, and then the `ResultMessage` that ends the run.

**Check it.** Export your key in the same shell that starts the app (the app does not read `.env`), restart the server:

```bash
export ANTHROPIC_API_KEY=sk-...
uv run python run.py
```

Open **Milo Ledger 2026 (needs review)** and click **Run AI review**.

Once the agent is done and the page refreshes, the page still shows the "no report" error, because you return `None`. Look at the terminal instead. You should see a `TOOL: Read` line for `manifest.json`, then an `AGENT:` line that names the attached W-2 and 1099-INT:

```text
TOOL: Read {'file_path': '/tmp/review-abc123/manifest.json'}
AGENT: Two documents are attached to this return, according to `manifest.json`:

| # | Stored file | Uploaded as |
|---|-------------|-------------|
| 1 | `documents/1099-int-decimal-dreams-2026.txt` | `1099-int-decimal-dreams-2026.pdf` |
| 2 | `documents/w2-paperclip-2026.txt` | `w2-paperclip-2026.pdf` |

- **1099-INT:** interest income from "Decimal Dreams" for 2026.
- **W-2:** wage income from "Paperclip" for 2026.

The manifest only gives file names. I haven't opened either document, so I can't confirm what's in them. The `.txt` files in `documents/` are text versions of the uploaded PDFs. I can read them and pull out the figures if you want.
```

## 1b: Decide what the agent can touch

The agent reads tax data, so decide up front what it can do. Four options control this, and `tools`, `allowed_tools` and `permission_mode` are easy to mix up. You already set all four in 1a. Here is what each does:

| Option                      | What it does                                                                                        |
| --------------------------- | --------------------------------------------------------------------------------------------------- |
| `cwd=str(workspace)`        | The folder the agent starts in. It is the review folder, so `manifest.json` is one file name away. |
| `tools=['Read']`            | Chooses which built-in tools exist at all. Without it, the agent also gets a shell and file writes. |
| `allowed_tools=['Read']`    | Pre-approves tools so they run without asking. It does not remove anything.                         |
| `permission_mode='dontAsk'` | Denies anything not pre-approved instead of prompting. Nobody is there to click "allow".            |

The remaining 1a options keep your own machine out of the review:

| Option                                      | What it does                                                                                                              |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| `model='claude-opus-5-5'`                   | Pins the model this lab was tested on, so results match the expected ones.                                                |
| `setting_sources=[]`                        | Loads no user, project or local settings or `CLAUDE.md`. If you omit it, all three load. Step 2 turns on what it needs.   |
| `mcp_servers={}, strict_mcp_config=True`    | Ignores MCP servers configured on your machine.                                                                           |
| `env={'CLAUDE_CODE_DISABLE_AUTO_MEMORY': '1'}` | Turns off auto memory, so nothing from earlier sessions leaks in.                                                      |

## 1c: Put a ceiling on the run

An agent runs until it decides it is done. If it gets stuck, say by rereading the same file, nothing stops it from running up a bill. The two limits you set in 1a are the safety net: `max_turns=30` and `max_budget_usd=1.00`.

A turn is one round of Claude responding and tools running. The reviews in this lab take roughly 6 to 12 turns and cost $0.10 to $0.16, because later steps add skills and a subagent. 30 turns and $1.00 leave room for all of them without letting a stuck run go on, so you will not need to change these limits in later steps. They are starting points. After your first full run, the Summary page shows the real cost and turns. `max_budget_usd` is an estimate and can overshoot.

A run that hits either limit ends with a result that is not a success. You handle that in 1f.

## 1d: Write the system prompt

The system prompt is the agent's job description, and right now it carries every rule the reviewer follows. Keep it short and concrete.

Include:

- The role and its limits: what the agent is, and that it only reads and recommends.
- The files in the folder and what each is for. The file tree in ["What is already built"](LAB.md#what-is-already-built) lists them.
- What to do with the app's own findings.
- What each verdict means, so results are consistent. The [verdict table](LAB.md#the-scenario) is in the overview.

Leave out:

- The report format. The schema in 1e handles that.
- Tax law lectures and long example cases. The agent reads everything you add on every run, and more text can confuse it.
- Instructions the agent has no tool for, such as "email the taxpayer".

Add this skeleton above `run_review` and fill in the blanks:

```python
SYSTEM_PROMPT = """You are ... (the role and its limits)

The working folder holds:
- ... (one line per file)

... (what to do with the app's findings, and how to compare each document with the return)

Verdicts:
- hold: ...
- warn: ...
- pass: ...
"""
```

<details>
<summary>Show a working prompt</summary>

```python
SYSTEM_PROMPT = """You are the pre-filing reviewer for MyTaxUSA, a fictional tax preparation product.
You review one taxpayer's return before they file it. You only read and recommend. You never change anything.

The working folder holds:
- return.json: this year's return
- prior.json: last year's return, or null
- diagnostics.json: the app's own findings. Report them. Do not re-derive them.
- manifest.json: the list of attached documents. Their text is in documents/

Read what you need. Compare each document with the return. Be specific and brief.

Verdicts:
- hold: a diagnostics error, or a document that disagrees with the return.
- warn: nothing blocks filing, but the taxpayer should answer a question.
- pass: everything checks out. Do not invent problems.
"""
```

</details>

Two lines in that prompt do most of the work. "Report them. Do not re-derive them" stops the agent from redoing the app's own checks. "Do not invent problems" keeps the clean return from being flagged.

Then pass the prompt to `ClaudeAgentOptions` and change the query to `'Review this return before the taxpayer files it.'`:

```python
            system_prompt=SYSTEM_PROMPT,
```

This prompt is a string inside your Python, so changing a rule means a code change. [Steps 2](LAB-step2.md) to [4](LAB-step4.md) take it apart.

**Check it.** Run the review again. The terminal should now show `Read` calls for `return.json`, `prior.json`, `diagnostics.json`, `manifest.json` and each document, followed by a prose review. It is not structured yet, which is the next piece.

## 1e: Ask for a structured report

So far the agent answers in prose. That works for a person reading it, but the app cannot act on it.

The point of MyTaxUSA is that CPAs only see the exceptions, so the app has to route each return without anyone reading it: a `hold` goes to a CPA, a `warn` shows the taxpayer a question, and a `pass` clears the return.

The Summary page also needs separate fields to show findings and questions, and the filing gate can only read `verdict` if it is a field, not a sentence.

Make the SDK return validated JSON in the shape `schema.py` defines by adding one more option:

```python
            output_format={'type': 'json_schema', 'schema': REPORT_JSON_SCHEMA},
```

The report arrives on the final `ResultMessage` as `structured_output`. Capture it, and print it for now. Add a branch to your message loop, and declare the variables above `async with`:

```python
        report, cost, turns = None, None, None
        async with ClaudeSDKClient(options=options) as client:
            await client.query('Review this return before the taxpayer files it.')
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    ...  # your print statements from 1a stay
                elif isinstance(message, ResultMessage):
                    cost, turns, report = message.total_cost_usd, message.num_turns, message.structured_output
                    print(json.dumps(report, indent=2))
```

Also change `return None` to `return None  # report is printed, not returned yet`. You will return it in the next piece.

**Check it.** Run the review. The terminal should print a JSON report with `verdict`, `summary`, `findings`, `client_questions` and `suspicious_content`. For the needs-review return, expect `hold` and a finding about the W-2 wages. The page still shows the "no report" error.

## 1f: Check the result before you trust it, then return it

A failed run can still carry a well-shaped `structured_output`, so never accept the report on its own.

Replace everything from `async for message in client.receive_response():` to the end of the function with this. It keeps your `print` statements, so you still see the loop in the terminal, and adds the audit append and the checks:

```python
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):        # plain text from Claude
                            print('AGENT:', block.text)
                        elif isinstance(block, ToolUseBlock):   # Claude asked to run a tool
                            print('TOOL:', block.name, block.input)
                            if block.name != 'StructuredOutput':
                                ctx.audit.append({'event': 'tool_call', 'tool': block.name, 'detail': json.dumps(block.input)})
                elif isinstance(message, ResultMessage):
                    if message.is_error or message.subtype != 'success':
                        raise RuntimeError(f'Review failed ({message.subtype}): {message.result}')
                    cost, turns, report = message.total_cost_usd, message.num_turns, message.structured_output
    if report is None:
        raise RuntimeError('The reviewer did not return a structured report.')
    problems = validate_report(report)
    if problems:
        raise ValueError('Invalid report: ' + '; '.join(problems))
    return ReviewOutcome(report=report, cost_usd=cost, turns=turns)
```

What each guard does:

- `is_error` or a `subtype` other than `success`: the run hit a limit or crashed. Raise, even if a report came back.
- `report is None`: the agent never produced a structured report.
- `validate_report`: checks the rules a schema cannot. A `pass` cannot carry a blocker or leave client questions open, and a `warn` cannot carry a blocker.
- `ctx.audit`: one entry per tool call, skipping the internal `StructuredOutput` call. The Summary page shows this list under the report.

The route in `app/routes/review.py` catches whatever you raise and shows it on the Summary page, so the page always tells you what happened.

## 1g: Run it and check the result

Restart the server and run **Milo Ledger 2026 (needs review)**. It works when all of these hold:

1. The page shows a report, not "Review failed". A run that ends in an error is rejected even if it carried a report.
2. The report passed `validate_report`, which your code enforces.
3. A finding cites the known W-2 mismatch with both values: wages 62,400 in the document and 52,400 in the return.
4. The audit list shows a `Read` of `w2-paperclip-2026.txt`, so the answer came from the document and not from a guess.

Stuck? Expand the complete file below and compare it with yours.

<details>
<summary>Solution: runner.py (complete file)</summary>

```python
"""The review agent.

STARTER FILE. Lab step 1 replaces `run_review` with a real agent built on the
Claude Agent SDK. Everything around it (the POST route, the saved review, the
report on the Summary page) is already wired up.

Contract:
  * `run_review(ctx)` is async. Return a `ReviewOutcome`, or raise.
  * `review_workspace(ctx)` (workspace.py) gives you a temporary folder holding this
    return's data and documents. Point the agent at it.
  * Append one dict per tool call to `ctx.audit`, like
    {'event': 'tool_call' | 'tool_denied', 'tool': 'Read', 'detail': '...'}.
    The page shows this list under the report.
  * Never write return data. The agent reads and recommends only.
"""
import json
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, ResultMessage, TextBlock, ToolUseBlock

from .schema import REPORT_JSON_SCHEMA, validate_report
from .workspace import review_workspace

SYSTEM_PROMPT = """You are the pre-filing reviewer for MyTaxUSA, a fictional tax preparation product.
You review one taxpayer's return before they file it. You only read and recommend. You never change anything.

The working folder holds:
- return.json: this year's return
- prior.json: last year's return, or null
- diagnostics.json: the app's own findings. Report them. Do not re-derive them.
- manifest.json: the list of attached documents. Their text is in documents/

Read what you need. Compare each document with the return. Be specific and brief.

Verdicts:
- hold: a diagnostics error, or a document that disagrees with the return.
- warn: nothing blocks filing, but the taxpayer should answer a question.
- pass: everything checks out. Do not invent problems.
"""


@dataclass
class ReviewContext:
    return_id: str
    owner: str
    snapshot: dict          # see snapshot.build_snapshot
    documents: Any          # DocumentService: .directory and .get(...) locate attached files
    audit: list = field(default_factory=list)


@dataclass
class ReviewOutcome:
    report: dict            # must pass schema.validate_report
    cost_usd: float | None = None
    turns: int | None = None


async def run_review(ctx: ReviewContext) -> ReviewOutcome:
    with review_workspace(ctx) as workspace:
        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            cwd=str(workspace),
            model='claude-opus-5-5',                     # pinned: the model this lab was tested on
            mcp_servers={}, strict_mcp_config=True,   # ignore MCP servers configured on this machine
            env={'CLAUDE_CODE_DISABLE_AUTO_MEMORY': '1'},   # no ambient auto memory
            tools=['Read'],   # the only built-in tool
            allowed_tools=['Read'],   # pre-approved
            permission_mode='dontAsk',                # anything else is denied, never prompted
            setting_sources=[],                       # do not load CLAUDE.md or settings from disk (yet)
            max_turns=30,
            max_budget_usd=1.00,
            output_format={'type': 'json_schema', 'schema': REPORT_JSON_SCHEMA},
        )
        report, cost, turns = None, None, None
        async with ClaudeSDKClient(options=options) as client:
            await client.query('Review this return before the taxpayer files it.')
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):        # plain text from Claude
                            print('AGENT:', block.text)
                        elif isinstance(block, ToolUseBlock):   # Claude asked to run a tool
                            print('TOOL:', block.name, block.input)
                            if block.name != 'StructuredOutput':
                                ctx.audit.append({'event': 'tool_call', 'tool': block.name, 'detail': json.dumps(block.input)})
                elif isinstance(message, ResultMessage):
                    if message.is_error or message.subtype != 'success':
                        raise RuntimeError(f'Review failed ({message.subtype}): {message.result}')
                    cost, turns, report = message.total_cost_usd, message.num_turns, message.structured_output
    if report is None:
        raise RuntimeError('The reviewer did not return a structured report.')
    problems = validate_report(report)
    if problems:
        raise ValueError('Invalid report: ' + '; '.join(problems))
    return ReviewOutcome(report=report, cost_usd=cost, turns=turns)
```

</details>

---

[Previous: Step 0](LAB-step0.md) | [Overview](LAB.md) | [Next: Step 2](LAB-step2.md) | [Stuck?](LAB-troubleshooting.md)
