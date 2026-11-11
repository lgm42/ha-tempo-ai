"""Config flow: URL of the Tempo AI server and optional API token."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_API_TOKEN, CONF_URL
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import TempoAIClient, TempoAIError
from .const import DOMAIN, LOGGER

try:  # Home Assistant 2026.10+ ships the voluptuous successor under this name
    import probatio as vol
except ImportError:  # pragma: no cover - older Home Assistant
    import voluptuous as vol

SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL): TextSelector(TextSelectorConfig(type=TextSelectorType.URL)),
        vol.Optional(CONF_API_TOKEN): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
    }
)


def _clean(user_input: dict[str, Any]) -> dict[str, Any]:
    data = {CONF_URL: user_input[CONF_URL].strip().rstrip("/")}
    if token := (user_input.get(CONF_API_TOKEN) or "").strip():
        data[CONF_API_TOKEN] = token
    return data


class TempoAIConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add a Tempo AI server."""

    VERSION = 1

    async def _test(self, data: dict[str, Any]) -> dict[str, str]:
        client = TempoAIClient(async_get_clientsession(self.hass), data[CONF_URL], data.get(CONF_API_TOKEN))
        try:
            health = await client.health()
        except TempoAIError:
            LOGGER.debug("Cannot reach Tempo AI at %s", data[CONF_URL], exc_info=True)
            return {"base": "cannot_connect"}
        if not isinstance(health, dict) or "version" not in health:
            return {"base": "invalid_response"}
        return {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """First step: server URL."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _clean(user_input)
            self._async_abort_entries_match({CONF_URL: data[CONF_URL]})
            if not (errors := await self._test(data)):
                return self.async_create_entry(title="Tempo AI", data=data)
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(SCHEMA, user_input),
            errors=errors,
            description_placeholders={"example": "http://192.168.1.10:31090"},
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Change the URL or the token."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _clean(user_input)
            if not (errors := await self._test(data)):
                return self.async_update_reload_and_abort(entry, data=data)
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(SCHEMA, user_input or entry.data),
            errors=errors,
        )
