"""Sensors: colors, probabilities, remaining days, success rates and service state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.util import dt as dt_util

from .const import COLORS, HORIZONS, STATUSES
from .coordinator import TempoAIConfigEntry
from .entity import TempoAIEntity, day, percent

PARALLEL_UPDATES = 0

Data = dict[str, Any]


@dataclass(frozen=True, kw_only=True)
class TempoAISensorEntityDescription(SensorEntityDescription):
    """Sensor reading one value of the summary."""

    value_fn: Callable[[Data], StateType | date | datetime]
    attr_fn: Callable[[Data], dict[str, Any]] = lambda _data: {}


def _timestamp(value: str | None) -> datetime | None:
    return dt_util.parse_datetime(value) if value else None


def _day_attributes(data: Data, horizon: int) -> dict[str, Any]:
    d = day(data, horizon)
    if not d:
        return {}
    attrs: dict[str, Any] = {"date": d.get("date")}
    if "source" in d:
        attrs["source"] = d["source"]  # "rte" = official color, "model" = forecast
    for color, p in (d.get("probabilities") or {}).items():
        attrs[f"probability_{color}"] = percent(p)
    for key in ("net_load_mw", "score", "threshold_white", "threshold_red"):
        if d.get(key) is not None:
            attrs[key] = d[key]
    return attrs


def _color(horizon: int, key: str) -> TempoAISensorEntityDescription:
    return TempoAISensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.ENUM,
        options=COLORS,
        value_fn=lambda data: (day(data, horizon) or {}).get("color"),
        attr_fn=lambda data: _day_attributes(data, horizon),
    )


def _probability(horizon: int, color: str) -> TempoAISensorEntityDescription:
    key = f"{color}_probability_d{horizon}"
    return TempoAISensorEntityDescription(
        key=key,
        translation_key=key,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda data: percent(((day(data, horizon) or {}).get("probabilities") or {}).get(color)),
    )


def _block(data: Data, period: str) -> Data:
    return (data.get("accuracy") or {}).get(period) or {}


def _accuracy_attributes(block: Data) -> dict[str, Any]:
    red_found = block.get("red_found") or {}
    red_alerts = block.get("red_alerts_right") or {}
    attrs = {
        "correct": block.get("correct"),
        "total": block.get("total"),
        "red_days_found": red_found.get("correct"),
        "red_days": red_found.get("total"),
        "red_alerts_right": red_alerts.get("correct"),
        "red_alerts": red_alerts.get("total"),
    }
    for horizon, b in (block.get("by_horizon") or {}).items():
        attrs[f"rate_{horizon.lower().replace('+', '')}"] = percent(b.get("rate"))
    return attrs


def _accuracy(period: str) -> TempoAISensorEntityDescription:
    key = f"accuracy_{period}"
    return TempoAISensorEntityDescription(
        key=key,
        translation_key=key,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: percent(_block(data, period).get("rate")),
        attr_fn=lambda data: _accuracy_attributes(_block(data, period)),
    )


def _accuracy_horizon(horizon: int) -> TempoAISensorEntityDescription:
    key = f"accuracy_d{horizon}"

    def block(data: Data) -> Data:
        return (_block(data, "overall").get("by_horizon") or {}).get(f"J+{horizon}") or {}

    return TempoAISensorEntityDescription(
        key=key,
        translation_key=key,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: percent(block(data).get("rate")),
        attr_fn=lambda data: {"correct": block(data).get("correct"), "total": block(data).get("total")},
    )


def _stock(color: str) -> TempoAISensorEntityDescription:
    key = f"{color}_days_left"
    return TempoAISensorEntityDescription(
        key=key,
        translation_key=key,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: (data.get("stock") or {}).get(f"{color}_left"),
        attr_fn=lambda data: {
            "total": (data.get("stock") or {}).get(f"{color}_total"),
            "season": (data.get("stock") or {}).get("season"),
        },
    )


def _tracking_since(data: Data) -> date | None:
    value = (data.get("accuracy") or {}).get("tracking_since")
    return date.fromisoformat(value) if value else None


SENSORS: tuple[TempoAISensorEntityDescription, ...] = (
    _color(0, "color_today"),
    _color(1, "color_tomorrow"),
    *(_color(h, f"color_d{h}") for h in HORIZONS),
    *(_probability(h, c) for h in HORIZONS for c in ("white", "red")),
    _stock("white"),
    _stock("red"),
    *(_accuracy(p) for p in ("overall", "season", "month", "last_7_days")),
    *(_accuracy_horizon(h) for h in HORIZONS),
    TempoAISensorEntityDescription(
        key="tracking_since",
        translation_key="tracking_since",
        device_class=SensorDeviceClass.DATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_tracking_since,
    ),
    TempoAISensorEntityDescription(
        key="predictions_evaluated",
        translation_key="predictions_evaluated",
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (data.get("accuracy") or {}).get("predictions_evaluated"),
        attr_fn=lambda data: {"predictions_issued": (data.get("accuracy") or {}).get("predictions_issued")},
    ),
    TempoAISensorEntityDescription(
        key="last_training",
        translation_key="last_training",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _timestamp((data.get("model") or {}).get("trained_at")),
        attr_fn=lambda data: {
            k: (data.get("model") or {}).get(k) for k in ("version", "training_days", "data_from", "data_to")
        },
    ),
    TempoAISensorEntityDescription(
        key="forecast_issued_at",
        translation_key="forecast_issued_at",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _timestamp(data.get("forecast_issued_at")),
    ),
    TempoAISensorEntityDescription(
        key="next_daily_run",
        translation_key="next_daily_run",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: _timestamp((data.get("app") or {}).get("next_daily_run")),
    ),
    TempoAISensorEntityDescription(
        key="status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        options=STATUSES,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: (data.get("app") or {}).get("status"),
        attr_fn=lambda data: {k: (data.get("app") or {}).get(k) for k in ("task", "message", "version")},
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TempoAIConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors."""
    coordinator = entry.runtime_data
    async_add_entities(TempoAISensor(coordinator, description) for description in SENSORS)


class TempoAISensor(TempoAIEntity, SensorEntity):
    """Tempo AI sensor."""

    entity_description: TempoAISensorEntityDescription

    @property
    def native_value(self) -> StateType | date | datetime:
        """Current value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Details: date, probabilities, counts."""
        return self.entity_description.attr_fn(self.coordinator.data)
