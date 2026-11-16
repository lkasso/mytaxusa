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
