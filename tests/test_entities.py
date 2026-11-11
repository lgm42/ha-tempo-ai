"""Entities created from a summary."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tempo_ai.api import TempoAIAuthError, TempoAIBusyError, TempoAIConnectionError
from custom_components.tempo_ai.const import DOMAIN
from custom_components.tempo_ai.diagnostics import async_get_config_entry_diagnostics
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def _entity_id(hass: HomeAssistant, entry: MockConfigEntry, platform: str, key: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{entry.entry_id}_{key}")
    assert entity_id, f"{platform} {key} not created"
    return entity_id


def _state(hass: HomeAssistant, entry: MockConfigEntry, platform: str, key: str):
    return hass.states.get(_entity_id(hass, entry, platform, key))


async def test_colors(hass: HomeAssistant, config_entry: MockConfigEntry, client: AsyncMock) -> None:
    await _setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED

    assert _state(hass, config_entry, "sensor", "color_today").state == "blue"
    tomorrow = _state(hass, config_entry, "sensor", "color_tomorrow")
    assert tomorrow.state == "blue"
    assert tomorrow.attributes["source"] == "rte"

    d2 = _state(hass, config_entry, "sensor", "color_d2")
    assert d2.state == "blue"
    assert d2.attributes["date"] == "2026-11-13"
    assert d2.attributes["probability_blue"] == 99.5
    assert d2.attributes["net_load_mw"] == 49764
    assert _state(hass, config_entry, "sensor", "color_d3").state == "white"
    assert _state(hass, config_entry, "sensor", "color_d4").state == "red"


async def test_stocks_and_accuracy(hass: HomeAssistant, config_entry: MockConfigEntry, client: AsyncMock) -> None:
    await _setup(hass, config_entry)

    white = _state(hass, config_entry, "sensor", "white_days_left")
    assert white.state == "42"
    assert white.attributes["total"] == 43
    assert _state(hass, config_entry, "sensor", "red_days_left").state == "22"

    overall = _state(hass, config_entry, "sensor", "accuracy_overall")
    assert float(overall.state) == 87.5
    assert overall.attributes["correct"] == 21
    assert overall.attributes["rate_j2"] == 100.0
    assert overall.attributes["red_days_found"] == 1
    assert float(_state(hass, config_entry, "sensor", "accuracy_month").state) == pytest.approx(85.7)
    assert float(_state(hass, config_entry, "sensor", "accuracy_last_7_days").state) == pytest.approx(85.7)
    assert float(_state(hass, config_entry, "sensor", "accuracy_d4").state) == 75.0

    assert _state(hass, config_entry, "sensor", "tracking_since").state == "2026-11-11"
    assert _state(hass, config_entry, "sensor", "last_training").state == "2026-11-11T13:15:20+00:00"
    assert _state(hass, config_entry, "sensor", "status").state == "ready"


async def test_probabilities_disabled_by_default(
    hass: HomeAssistant, config_entry: MockConfigEntry, client: AsyncMock
) -> None:
    await _setup(hass, config_entry)
    entity_id = _entity_id(hass, config_entry, "sensor", "red_probability_d4")
    assert er.async_get(hass).async_get(entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION
    assert hass.states.get(entity_id) is None


async def test_no_data_yet(
    hass: HomeAssistant, config_entry: MockConfigEntry, client: AsyncMock, summary: dict
) -> None:
    """Server still initializing: no forecast, no model, no rate."""
    summary.update(today=None, tomorrow=None, forecast=[], stock=None, model=None)
    summary["app"]["status"] = "initializing"
    summary["accuracy"]["overall"]["rate"] = None
    await _setup(hass, config_entry)
    assert _state(hass, config_entry, "sensor", "color_d2").state == "unknown"
    assert _state(hass, config_entry, "sensor", "white_days_left").state == "unknown"
    assert _state(hass, config_entry, "sensor", "accuracy_overall").state == "unknown"
    assert _state(hass, config_entry, "sensor", "status").state == "initializing"
    assert _state(hass, config_entry, "binary_sensor", "red_day_expected").state == "off"


async def test_binary_sensors(hass: HomeAssistant, config_entry: MockConfigEntry, client: AsyncMock) -> None:
    await _setup(hass, config_entry)
    red = _state(hass, config_entry, "binary_sensor", "red_day_expected")
    assert red.state == "on"
    assert red.attributes["dates"] == ["2026-11-15"]
    assert _state(hass, config_entry, "binary_sensor", "white_day_expected").attributes["dates"] == ["2026-11-14"]


async def test_server_unreachable(hass: HomeAssistant, config_entry: MockConfigEntry, client: AsyncMock) -> None:
    client.summary.side_effect = TempoAIConnectionError("timeout")
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_refresh_button(hass: HomeAssistant, config_entry: MockConfigEntry, client: AsyncMock) -> None:
    await _setup(hass, config_entry)
    entity_id = _entity_id(hass, config_entry, "button", "refresh_forecast")
    calls = client.summary.call_count
    await hass.services.async_call("button", "press", {"entity_id": entity_id}, blocking=True)
    client.refresh.assert_awaited_once()
    await hass.async_block_till_done()
    assert client.summary.call_count > calls


@pytest.mark.parametrize(
    ("error", "key"),
    [
        (TempoAIAuthError("401"), "invalid_token"),
        (TempoAIBusyError("tâche en cours : training"), "busy"),
        (TempoAIConnectionError("timeout"), "cannot_connect"),
    ],
)
async def test_button_errors(
    hass: HomeAssistant, config_entry: MockConfigEntry, client: AsyncMock, error: Exception, key: str
) -> None:
    await _setup(hass, config_entry)
    client.train.side_effect = error
    entity_id = _entity_id(hass, config_entry, "button", "retrain")
    with pytest.raises(HomeAssistantError) as exc:
        await hass.services.async_call("button", "press", {"entity_id": entity_id}, blocking=True)
    assert exc.value.translation_key == key


async def test_unload(hass: HomeAssistant, config_entry: MockConfigEntry, client: AsyncMock) -> None:
    await _setup(hass, config_entry)
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED


async def test_diagnostics_redact_token(
    hass: HomeAssistant, config_entry: MockConfigEntry, client: AsyncMock
) -> None:
    await _setup(hass, config_entry)
    diag = await async_get_config_entry_diagnostics(hass, config_entry)
    assert diag["entry"]["api_token"] == "**REDACTED**"
    assert diag["summary"]["app"]["version"] == "0.1.0"


async def test_entity_ids(hass: HomeAssistant, config_entry: MockConfigEntry, client: AsyncMock) -> None:
    """Entity IDs used in the README examples (English)."""
    await _setup(hass, config_entry)
    for entity_id in (
        "sensor.tempo_ai_color_tomorrow",
        "sensor.tempo_ai_color_d_2",
        "sensor.tempo_ai_color_d_4",
        "sensor.tempo_ai_red_days_left",
        "sensor.tempo_ai_success_rate",
        "binary_sensor.tempo_ai_red_day_expected",
        "button.tempo_ai_recompute_forecast",
    ):
        assert hass.states.get(entity_id), entity_id
