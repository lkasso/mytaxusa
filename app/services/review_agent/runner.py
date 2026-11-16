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
