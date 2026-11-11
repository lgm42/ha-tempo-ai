"""Config flow: add and reconfigure a server."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tempo_ai.api import TempoAIConnectionError
from custom_components.tempo_ai.const import DOMAIN
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_API_TOKEN, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import URL


@pytest.fixture
def health() -> Generator[AsyncMock]:
    with patch("custom_components.tempo_ai.config_flow.TempoAIClient.health", autospec=True) as mock:
        mock.return_value = {"status": "ready", "version": "0.1.0"}
        yield mock


@pytest.fixture(autouse=True)
def no_setup() -> Generator[None]:
    with patch("custom_components.tempo_ai.async_setup_entry", return_value=True):
        yield


async def test_user_flow(hass: HomeAssistant, health: AsyncMock) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: f" {URL}/ ", CONF_API_TOKEN: " secret "}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Tempo AI"
    assert result["data"] == {CONF_URL: URL, CONF_API_TOKEN: "secret"}


async def test_user_flow_without_token(hass: HomeAssistant, health: AsyncMock) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL})
    assert result["data"] == {CONF_URL: URL}


async def test_cannot_connect_then_recover(hass: HomeAssistant, health: AsyncMock) -> None:
    health.side_effect = TempoAIConnectionError("refused")
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

    health.side_effect = None
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_not_a_tempo_ai_server(hass: HomeAssistant, health: AsyncMock) -> None:
    health.return_value = {"status": "ok"}
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL})
    assert result["errors"] == {"base": "invalid_response"}


async def test_already_configured(hass: HomeAssistant, health: AsyncMock, config_entry: MockConfigEntry) -> None:
    config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL + "/"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure(hass: HomeAssistant, health: AsyncMock, config_entry: MockConfigEntry) -> None:
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: "http://nas:31090", CONF_API_TOKEN: ""}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.data == {CONF_URL: "http://nas:31090"}
