"""REST client: requests and error mapping."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.tempo_ai.api import (
    TempoAIAuthError,
    TempoAIBusyError,
    TempoAIClient,
    TempoAIConnectionError,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .conftest import URL


def _client(hass: HomeAssistant, token: str | None = None) -> TempoAIClient:
    return TempoAIClient(async_get_clientsession(hass), URL + "/", token)


async def test_summary(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(f"{URL}/api/summary", json={"app": {"version": "0.1.0"}})
    assert await _client(hass).summary() == {"app": {"version": "0.1.0"}}


async def test_token_sent(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.post(f"{URL}/api/train", status=202, json={"started": "training"})
    await _client(hass, "secret").train()
    assert aioclient_mock.mock_calls[0][3] == {"Authorization": "Bearer secret"}


async def test_refresh(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get(f"{URL}/api/forecast?refresh=true", json={"issued_for": "2026-11-11"})
    assert (await _client(hass).refresh())["issued_for"] == "2026-11-11"


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"status": 401, "json": {"detail": "jeton invalide"}}, TempoAIAuthError),
        ({"status": 409, "json": {"detail": "tâche en cours"}}, TempoAIBusyError),
        ({"status": 500, "text": "boom"}, TempoAIConnectionError),
        ({"exc": TimeoutError()}, TempoAIConnectionError),
    ],
)
async def test_errors(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, kwargs: dict, error: type) -> None:
    aioclient_mock.post(f"{URL}/api/train", **kwargs)
    with pytest.raises(error):
        await _client(hass, "secret").train()


async def test_busy_detail(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.post(f"{URL}/api/train", status=409, json={"detail": "tâche en cours : daily_forecast"})
    with pytest.raises(TempoAIBusyError, match="daily_forecast"):
        await _client(hass).train()
