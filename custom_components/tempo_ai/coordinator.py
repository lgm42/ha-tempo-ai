"""Data update coordinator: one call to /api/summary every 10 minutes."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TempoAIClient, TempoAIError
from .const import DOMAIN, LOGGER, SCAN_INTERVAL

type TempoAIConfigEntry = ConfigEntry[TempoAICoordinator]


class TempoAICoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches the summary of a Tempo AI server."""

    config_entry: TempoAIConfigEntry

    def __init__(self, hass: HomeAssistant, entry: TempoAIConfigEntry, client: TempoAIClient) -> None:
        super().__init__(hass, LOGGER, config_entry=entry, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.summary()
        except TempoAIError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="cannot_connect",
                translation_placeholders={"error": str(err)},
            ) from err
