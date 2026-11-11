"""Constants for the Tempo AI integration."""

from __future__ import annotations

from datetime import timedelta
import logging

DOMAIN = "tempo_ai"
LOGGER = logging.getLogger(__package__)

SCAN_INTERVAL = timedelta(minutes=10)

COLORS = ["blue", "white", "red"]
STATUSES = ["starting", "initializing", "ready", "busy", "error"]
HORIZONS = [2, 3, 4]
