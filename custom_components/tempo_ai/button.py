"""Buttons: recompute the forecast now, retrain the models."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import TempoAIAuthError, TempoAIBusyError, TempoAIClient, TempoAIError
from .const import DOMAIN
from .coordinator import TempoAIConfigEntry
from .entity import TempoAIEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class TempoAIButtonEntityDescription(ButtonEntityDescription):
    """Button calling one action of the API."""

    press_fn: Callable[[TempoAIClient], Awaitable[Any]]


BUTTONS = (
    TempoAIButtonEntityDescription(
        key="refresh_forecast",
        translation_key="refresh_forecast",
        press_fn=lambda client: client.refresh(),
    ),
    TempoAIButtonEntityDescription(
        key="retrain",
        translation_key="retrain",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda client: client.train(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TempoAIConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the buttons."""
    coordinator = entry.runtime_data
    async_add_entities(TempoAIButton(coordinator, description) for description in BUTTONS)


class TempoAIButton(TempoAIEntity, ButtonEntity):
    """Tempo AI action."""

    entity_description: TempoAIButtonEntityDescription

    async def async_press(self) -> None:
        """Call the API, then refresh the entities."""
        try:
            await self.entity_description.press_fn(self.coordinator.client)
        except TempoAIAuthError as err:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="invalid_token") from err
        except TempoAIBusyError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="busy", translation_placeholders={"detail": str(err)}
            ) from err
        except TempoAIError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="cannot_connect", translation_placeholders={"error": str(err)}
            ) from err
        await self.coordinator.async_request_refresh()
