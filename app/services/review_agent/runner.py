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
from dataclasses import dataclass, field
from typing import Any


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


async def run_review(ctx: ReviewContext) -> ReviewOutcome | None:
    return None  # TODO (lab step 1): build the agent
