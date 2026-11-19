"""Hands Lists's actions to voice assistants as Assist LLM tools.

Home Assistant (2026.11) asks every integration's llm.py for tools; without
this file an assistant sees none of these actions.
"""

from __future__ import annotations

import json

from homeassistant.components.llm import LLMTools
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.llm import LLM_API_ASSIST, ActionTool, LLMContext

from .const import DOMAIN
from .once import once

# The AI breakdown and brain-dump jobs are left out: up to 45 s is too long for a spoken reply.
ACTIONS = ("find_lists", "add_item", "create_list")

# Some agents load tools on demand (tool search): this line is how they
# learn the tools exist.
PROMPT = (
    "Task lists live in Lists: ha_lists__find_lists names them,"
    " ha_lists__add_item adds a task to one and ha_lists__create_list makes a new"
    " list. Groceries to buy go on the Storage shopping list instead."
)


# Everything else changes something, and must not do it twice on a replay.
READ_ONLY = ('find_lists',)


class OnceTool(ActionTool):
    """An action that changes something: a replayed call gets the first result."""

    async def async_call(self, hass, tool_input, llm_context):
        key = f"{self.name} {json.dumps(tool_input.tool_args, sort_keys=True, default=str)}"
        return await once(
            key, lambda: ActionTool.async_call(self, hass, tool_input, llm_context)
        )


@callback
def async_get_tools(
    hass: HomeAssistant, llm_context: LLMContext, api_id: str
) -> LLMTools | None:
    """Return Lists's tools for the Assist API."""
    if api_id != LLM_API_ASSIST:
        return None
    tools = [
        (ActionTool if action in READ_ONLY else OnceTool)(hass, DOMAIN, action)
        for action in ACTIONS
        if hass.services.has_service(DOMAIN, action)
    ]
    return LLMTools(tools=tools, prompt=PROMPT) if tools else None
