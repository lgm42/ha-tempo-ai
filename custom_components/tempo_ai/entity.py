"""Base entity: one service device per Tempo AI server."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TempoAICoordinator


class TempoAIEntity(CoordinatorEntity[TempoAICoordinator]):
    """Entity backed by the summary of a Tempo AI server."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TempoAICoordinator, description: EntityDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Tempo AI",
            manufacturer="Tempo AI",
            model="Tempo color forecast",
            sw_version=(coordinator.data.get("app") or {}).get("version"),
            configuration_url=coordinator.client.url,
            entry_type=DeviceEntryType.SERVICE,
        )


def day(data: dict[str, Any], horizon: int) -> dict[str, Any] | None:
    """Day at a given horizon: 0 = today, 1 = tomorrow, 2 to 4 = forecast."""
    if horizon == 0:
        return data.get("today")
    if horizon == 1:
        return data.get("tomorrow")
    return next((d for d in data.get("forecast") or [] if d.get("horizon") == horizon), None)


def percent(value: float | None) -> float | None:
    """Ratio (0-1) to a percentage."""
    return None if value is None else round(value * 100, 1)
