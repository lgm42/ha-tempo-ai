"""Diagnostics (the API token is redacted)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_TOKEN
from homeassistant.core import HomeAssistant

from .coordinator import TempoAIConfigEntry

TO_REDACT = {CONF_API_TOKEN}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: TempoAIConfigEntry) -> dict[str, Any]:
    """Config entry and last summary."""
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "summary": entry.runtime_data.data,
    }
