"""DataUpdateCoordinator for Elon Smart Water."""
from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

import aiohttp
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_PATH,
    API_TIMEOUT,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class ElonSmartWaterCoordinator(DataUpdateCoordinator[list[dict[str, Any]]]):
    """Coordinator to manage Elon Smart Water data fetching."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        scan_interval = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.host: str = entry.data[CONF_HOST]
        self.port: int = entry.data.get(CONF_PORT, DEFAULT_PORT)
        self.entry = entry

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Fetch data from the Elon Smart Water device."""
        url = f"http://{self.host}:{self.port}{API_PATH}"
        try:
            async with async_timeout.timeout(API_TIMEOUT):
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        response.raise_for_status()
                        data = await response.json(content_type=None)
                        return data.get("deviceStatuses", [])
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout communicating with {url}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(
                f"Error communicating with API at {url}: {err}"
            ) from err
        except Exception as err:
            raise UpdateFailed(
                f"Unexpected error fetching data from {url}: {err}"
            ) from err
