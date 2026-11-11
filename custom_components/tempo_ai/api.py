"""Small async client for the Tempo AI REST API."""

from __future__ import annotations

from typing import Any

import aiohttp


class TempoAIError(Exception):
    """Base error."""


class TempoAIConnectionError(TempoAIError):
    """The server cannot be reached or answered with an error."""


class TempoAIAuthError(TempoAIError):
    """The API token is missing or wrong."""


class TempoAIBusyError(TempoAIError):
    """A task (training, forecast) is already running on the server."""


class TempoAIClient:
    """Client for a Tempo AI server."""

    def __init__(self, session: aiohttp.ClientSession, url: str, token: str | None = None) -> None:
        self._session = session
        self.url = url.rstrip("/")
        self._token = token or None

    async def _request(self, method: str, path: str, timeout: int = 30, **params: str) -> Any:
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        try:
            async with self._session.request(
                method,
                f"{self.url}{path}",
                headers=headers,
                params=params or None,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status == 401:
                    raise TempoAIAuthError("invalid API token")
                if resp.status == 409:
                    raise TempoAIBusyError(await _detail(resp))
                resp.raise_for_status()
                return await resp.json()
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise TempoAIConnectionError(str(err) or err.__class__.__name__) from err

    async def health(self) -> dict[str, Any]:
        """Service status and version."""
        return await self._request("GET", "/api/health")

    async def summary(self) -> dict[str, Any]:
        """Everything in one request: forecasts, stocks, success rates, model."""
        return await self._request("GET", "/api/summary")

    async def refresh(self) -> dict[str, Any]:
        """Collect fresh data and recompute the forecast now (a few seconds)."""
        return await self._request("GET", "/api/forecast", timeout=300, refresh="true")

    async def train(self) -> dict[str, Any]:
        """Start a retraining in the background."""
        return await self._request("POST", "/api/train")


async def _detail(resp: aiohttp.ClientResponse) -> str:
    try:
        return str((await resp.json()).get("detail", ""))
    except (aiohttp.ContentTypeError, ValueError):
        return ""
