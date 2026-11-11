"""bsc-mint-guard plugin. Registration for Hermes."""

import logging
from pathlib import Path

from . import schemas, tools

logger = logging.getLogger(__name__)

_call_count = 0


def _on_post_tool_call(tool_name, args, result, task_id, **kwargs):
    """Hook: runs after every tool call. Logs the count only.

    No tool arguments, results, addresses, or user data are logged.
    """
    global _call_count
    _call_count += 1
    logger.debug("post_tool_call count: %d", _call_count)


def get_call_count():
    """Return how many post_tool_call events this plugin has seen."""
    return _call_count


def register(ctx):
    """Wire schemas to handlers, register the hook, and bundle the skill."""
    ctx.register_tool(
        name="mint_check",
        toolset="bsc-mint-guard",
        schema=schemas.MINT_CHECK,
        handler=tools.mint_check,
    )
    ctx.register_tool(
        name="mint_quote",
        toolset="bsc-mint-guard",
        schema=schemas.MINT_QUOTE,
        handler=tools.mint_quote,
    )
    ctx.register_tool(
        name="wallet_mint_status",
        toolset="bsc-mint-guard",
        schema=schemas.WALLET_MINT_STATUS,
        handler=tools.wallet_mint_status,
    )
    ctx.register_hook("post_tool_call", _on_post_tool_call)
    register_skill = getattr(ctx, "register_skill", None)
    if callable(register_skill):
        skills_dir = Path(__file__).parent / "skills"
        for child in sorted(skills_dir.iterdir()):
            skill_md = child / "SKILL.md"
            if child.is_dir() and skill_md.exists():
                register_skill(child.name, skill_md)
