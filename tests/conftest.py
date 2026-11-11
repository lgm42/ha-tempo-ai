"""Shared fixtures."""

from __future__ import annotations

from collections.abc import Generator
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tempo_ai.const import DOMAIN
from homeassistant.const import CONF_API_TOKEN, CONF_URL

URL = "http://tempo.local:31090"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load custom_components/ in every test."""


@pytest.fixture
def summary() -> dict[str, Any]:
    """Summary of a running server: D+2 blue, D+3 white, D+4 red, 24 forecasts evaluated."""
    return json.loads((Path(__file__).parent / "fixtures" / "summary.json").read_text(encoding="utf-8"))


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Config entry with a token."""
    return MockConfigEntry(domain=DOMAIN, title="Tempo AI", data={CONF_URL: URL, CONF_API_TOKEN: "secret"})


@pytest.fixture
def client(summary: dict[str, Any]) -> Generator[AsyncMock]:
    """Mocked API client used by the integration."""
    with patch("custom_components.tempo_ai.TempoAIClient", autospec=True) as cls:
        mock = cls.return_value
        mock.url = URL
        mock.summary.return_value = summary
        mock.health.return_value = {"status": "ready", "version": "0.1.0"}
        yield mock
