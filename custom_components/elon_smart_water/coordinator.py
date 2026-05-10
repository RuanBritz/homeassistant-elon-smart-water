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
from homeassistant.helpers.aiohttp_client import async_get_clientsession
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
        session = async_get_clientsession(self.hass)
        try:
            async with async_timeout.timeout(API_TIMEOUT):
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

    async def async_send_thermostat_command(
        self, command_path: str, device_serial: int, auth_id: str = ""
    ) -> None:
        """Send a thermostat command to the Elon Smart Water device."""
        url = f"http://{self.host}:{self.port}{command_path}"
        payload: dict[str, Any] = {"authId": auth_id, "deviceSerial": device_serial}
        session = async_get_clientsession(self.hass)
        headers = {
            "accept": "application/json",
            "accept-encoding": "gzip",
            "content-type": "application/json",
            "host": "elonsmartiot.com",
            "user-agent": "Dart/3.10 (dart:io)",
        }
        try:
            async with async_timeout.timeout(API_TIMEOUT):
                async with session.put(
                    url, json=payload, headers=headers
                ) as response:
                    response.raise_for_status()
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout communicating with {url}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(
                f"Error sending thermostat command to {url}: {err}"
            ) from err
        except Exception as err:
            raise UpdateFailed(
                f"Unexpected error sending thermostat command to {url}: {err}"
            ) from err
