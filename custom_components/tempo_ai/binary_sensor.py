"""Binary sensors: a white or red day is expected in the coming days (D+1 to D+4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import TempoAIConfigEntry
from .entity import TempoAIEntity, day

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class TempoAIBinarySensorEntityDescription(BinarySensorEntityDescription):
    """On when one of the next days has this color."""

    color: str


BINARY_SENSORS = (
    TempoAIBinarySensorEntityDescription(key="red_day_expected", translation_key="red_day_expected", color="red"),
    TempoAIBinarySensorEntityDescription(
        key="white_day_expected", translation_key="white_day_expected", color="white"
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TempoAIConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the binary sensors."""
    coordinator = entry.runtime_data
    async_add_entities(TempoAIBinarySensor(coordinator, description) for description in BINARY_SENSORS)


class TempoAIBinarySensor(TempoAIEntity, BinarySensorEntity):
    """A day of the given color is expected from D+1 to D+4."""

    entity_description: TempoAIBinarySensorEntityDescription

    def _dates(self) -> list[str]:
        days = (day(self.coordinator.data, h) for h in (1, 2, 3, 4))
        return [d["date"] for d in days if d and d.get("color") == self.entity_description.color]

    @property
    def is_on(self) -> bool:
        """True when at least one of the next 4 days has the color."""
        return bool(self._dates())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Dates with that color."""
        return {"dates": self._dates()}
