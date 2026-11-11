"""Tempo AI: local forecast of the French Tempo electricity color at D+2, D+3 and D+4."""

from __future__ import annotations

from homeassistant.const import CONF_API_TOKEN, CONF_URL, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TempoAIClient
from .coordinator import TempoAIConfigEntry, TempoAICoordinator

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: TempoAIConfigEntry) -> bool:
    """Set up Tempo AI from a config entry."""
    client = TempoAIClient(async_get_clientsession(hass), entry.data[CONF_URL], entry.data.get(CONF_API_TOKEN))
    coordinator = TempoAICoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TempoAIConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
