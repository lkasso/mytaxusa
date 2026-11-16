[Previous: Step 4](LAB-step4.md) | [Overview](LAB.md) | [Next: Run your agent](LAB-acceptance.md) | [Stuck?](LAB-troubleshooting.md)

# Step 5: Hooks (10 min)

**Create:** `app/services/review_agent/hooks.py`
**Edit:** `runner.py`

## 5a: Why hooks

Everything so far asked the model to behave. `CLAUDE.md` says "do not read documents yourself", and the model usually listens. Usually is not good enough for a tax review.

A hook is a Python function in your app that the SDK calls around every tool call. The model cannot talk its way past it, because the rule runs in your code, outside the model.

You will write one hook, a `PreToolUse` hook that runs before each tool call and denies anything out of bounds:

- any tool not on an allowlist (this also keeps `WebSearch` and `WebFetch` out, so the reviewer cannot browse);
- `Read` on a path outside the workspace.

The tool list in `runner.py` is already small, with no `Glob` or `Grep`, and that is on purpose. A hook that checks where a search starts does not check everything a recursive search can read. `Grep` with `path` set to the workspace and `pattern='.'` would sweep `documents/`. The less a tool can do, the less a hook has to police.

Hooks also fire inside subagents, so these rules cover the `document-checker` too.

## 5b: Start `hooks.py` with an allowlist

Create `app/services/review_agent/hooks.py`. This skeleton runs, but it allows everything until you fill in the two TODOs:

```python
"""Guardrails that run in our code, outside the model.

A prompt asks the model to behave. A hook decides what actually happens.
"""
from pathlib import Path

from claude_agent_sdk import HookMatcher

ALLOWED = set()   # TODO: the tool names the reviewer and its subagents may use


def build_hooks(ctx):
    async def before_tool(input_data, tool_use_id, context):
        """Runs before every tool call, for the reviewer and for every subagent."""
        name, args = input_data['tool_name'], input_data['tool_input']
        reason = None
        # TODO rule 1: if `name` is not in ALLOWED, set `reason` to a sentence saying so.
        if reason:
            ctx.audit.append({'event': 'tool_denied', 'tool': name, 'detail': reason})
            return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                                           'permissionDecisionReason': reason}}
        return {}

    return {'PreToolUse': [HookMatcher(hooks=[before_tool])]}
```

Three things to know about the skeleton:

- `input_data` describes the tool call: `tool_name`, `tool_input`, and `cwd` (the workspace).
- Returning `{}` means "no opinion", so the call goes ahead. Returning the `permissionDecision: 'deny'` dictionary stops it, and Claude sees your `permissionDecisionReason` as the tool's answer.
- A denial is also appended to `ctx.audit`, so it shows on the page under the report.

Which tools belong in `ALLOWED`? The ones you listed in `tools` for step 4, plus one you did not list.

<details>
<summary>Show the working allowlist</summary>

```python
ALLOWED = {'Read', 'Skill', 'Agent', 'StructuredOutput'}  # StructuredOutput returns the final report
```

Replace the rule 1 TODO with:

```python
        if name not in ALLOWED:
            reason = f'{name} is not an approved review tool.'
```

</details>

**Do not leave out `StructuredOutput`.** The final report comes back through a tool with that name. If the allowlist denies it, every review fails with "did not return a structured report". The unit test checks that your hook allows `StructuredOutput`. A live run checks that the runtime can produce and return the structured report.

## 5c: Keep `Read` inside the workspace

`Read` is allowed, but it should only read the review folder. Add this line under the `name, args = ...` line, then add a branch for `Read` after the allowlist rule:

```python
        workspace = Path(input_data['cwd']).resolve()
```

```python
        # TODO rule 2: elif name == 'Read':
        #   resolve the path the model asked for, and if it is not inside `workspace`,
        #   set `reason` to 'That path is outside the review folder.'
```

Resolve the path before you compare it. Without `.resolve()`, a path like `workspace/../../etc/hosts` looks like it starts inside the workspace and is not. `Path.is_relative_to` does the comparison.

<details>
<summary>Show the working rule</summary>

```python
        elif name == 'Read':
            target = (workspace / args.get('file_path', '')).resolve()
            if not target.is_relative_to(workspace):
                reason = 'That path is outside the review folder.'
```

</details>

## 5d: Wire the hook into `runner.py`

Two edits in `runner.py`:

1. Import the builder, next to the other imports from this package:

   ```python
   from .hooks import build_hooks
   ```

2. Pass the hooks in `ClaudeAgentOptions`:

   ```python
               hooks=build_hooks(ctx),                   # our rules run before every tool call
   ```

The message loop stays as it is, including the `print` statements and the audit rows. Your hook adds its own `tool_denied` row whenever it blocks a call, so denials show on the page next to the normal rows.

Then make one more change, in `hooks.py`. Register the pre-tool hook with `on_failure='block'`:

```python
    return {'PreToolUse': [HookMatcher(hooks=[before_tool], on_failure='block')]}
```

Without it, a hook that raises an exception falls through to normal permission handling instead of stopping the call. A bug in your guardrail would quietly open the gate. With `block`, the call is stopped if the hook fails. That is why every path through `before_tool` must end in a deny dictionary or `{}`.

## 5e: Check it

Run **Milo Ledger 2026 (needs review)**. The review should still complete and return `hold`, and the terminal should look the same as in step 4. If it fails with "did not return a structured report", go back to the `StructuredOutput` warning in 5b.

## 5f: Run the tests

The rules are plain Python, so you can test them without calling the model. The repo already includes `tests/test_review_hooks.py`. It skips itself until `hooks.py` exists, so you do not need to write it. Run:

```bash
uv run python -m unittest tests.test_review_hooks -v
```

Six tests should pass. They call your hook directly with a made-up `input_data` and check that `Bash`, `Glob`, `Grep`, `WebSearch` and `WebFetch` are denied, that a `Read` outside the workspace is denied, and that `return.json` and `StructuredOutput` are allowed. Open the file if you want to see how it calls the hook:

```text
test_bash_is_denied (tests.test_review_hooks.ReviewHookTests.test_bash_is_denied) ... ok
test_read_outside_folder_is_denied (tests.test_review_hooks.ReviewHookTests.test_read_outside_folder_is_denied) ... ok
test_return_json_is_allowed (tests.test_review_hooks.ReviewHookTests.test_return_json_is_allowed) ... ok
test_search_tools_are_denied (tests.test_review_hooks.ReviewHookTests.test_search_tools_are_denied) ... ok
test_structured_output_is_allowed (tests.test_review_hooks.ReviewHookTests.test_structured_output_is_allowed) ... ok
test_web_tools_are_denied (tests.test_review_hooks.ReviewHookTests.test_web_tools_are_denied) ... ok

----------------------------------------------------------------------
Ran 6 tests in 0.003s

OK
```

**Works when:**

1. The unit tests pass. They cover allowed and denied cases directly, including that your hook allows `StructuredOutput`. The live run in 5e checks that the runtime can produce and return the structured report.
2. A live review still completes and returns `hold`.
3. A normal run has no `tool_denied` rows. A denial on a normal run means a rule is too tight.

Stuck? Expand the complete files below and compare them with yours.

<details>
<summary>Solution: hooks.py (complete file)</summary>

```python
"""Guardrails that run in our code, outside the model.

A prompt asks the model to behave. A hook decides what actually happens.
"""
from pathlib import Path

from claude_agent_sdk import HookMatcher

ALLOWED = {'Read', 'Skill', 'Agent', 'StructuredOutput'}  # StructuredOutput returns the final report


def build_hooks(ctx):
    async def before_tool(input_data, tool_use_id, context):
        """Runs before every tool call, for the reviewer and for every subagent. Deny what is out of bounds."""
        name, args = input_data['tool_name'], input_data['tool_input']
        workspace = Path(input_data['cwd']).resolve()
        reason = None
        if name not in ALLOWED:
            reason = f'{name} is not an approved review tool.'
        elif name == 'Read':
            target = (workspace / args.get('file_path', '')).resolve()
            if not target.is_relative_to(workspace):
                reason = 'That path is outside the review folder.'
        if reason:
            ctx.audit.append({'event': 'tool_denied', 'tool': name, 'detail': reason})
            return {'hookSpecificOutput': {'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                                           'permissionDecisionReason': reason}}
        return {}

    return {'PreToolUse': [HookMatcher(hooks=[before_tool], on_failure='block')]}
```

</details>

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

from claude_agent_sdk import AgentDefinition, AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, ResultMessage, TextBlock, ToolResultBlock, ToolUseBlock, UserMessage

from .hooks import build_hooks
from .schema import REPORT_JSON_SCHEMA, validate_report
from .workspace import review_workspace

SYSTEM_PROMPT = "You are the pre-filing reviewer for MyTaxUSA. Follow the review standards in CLAUDE.md."


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
            tools=['Read', 'Skill', 'Agent'],   # built-in tools. No Glob or Grep: a recursive search could read past the hook's path check
            allowed_tools=['Read', 'Agent'],   # pre-approved
            agents={'document-checker': AgentDefinition(
                description='Ties one attached document to the return. Call once per document.',
                prompt='You tie one document to the return. Use the tie-out skill. Read the document you are given and return.json, '
                       'and report only the differences.',
                tools=['Read'],
                skills=['tie-out'],
                model='claude-haiku-5-5',          # a small, cheap model is enough for a narrow job
                background=False,       # the reviewer waits for the result
            )},
            skills=['prior-year-variance', 'credits-due-diligence'],   # skills the agent may load on demand
            permission_mode='dontAsk',                # anything else is denied, never prompted
            hooks=build_hooks(ctx),                   # our rules run before every tool call
            setting_sources=['project'],              # load CLAUDE.md from the working folder
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
                elif isinstance(message, UserMessage) and isinstance(message.content, list):
                    for block in message.content:           # tool results come back as user messages
                        if isinstance(block, ToolResultBlock):
                            status = 'ERROR' if block.is_error else 'ok'
                            print('RESULT:', status, str(block.content)[:200].replace('\n', ' '))
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

[Previous: Step 4](LAB-step4.md) | [Overview](LAB.md) | [Next: Run your agent](LAB-acceptance.md) | [Stuck?](LAB-troubleshooting.md)
