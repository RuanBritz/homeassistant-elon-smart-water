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
    API_CONFIG_PATH,
    API_MEASUREMENTS_PATH,
    API_PATH,
    API_TIMEOUT,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONFIG_PROPERTIES,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MEASUREMENTS_WINDOW,
    SENSOR_ID_ELEMENT_POWER,
    SENSOR_ID_SOLAR_INPUT,
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

    async def _fetch_sensor_measurement(
        self,
        session: aiohttp.ClientSession,
        device_serial: int,
        sensor_id: int,
        last_comms: int,
    ) -> float | None:
        """Fetch the latest measurement for a sensor from the device."""
        url = f"http://{self.host}:{self.port}{API_MEASUREMENTS_PATH}"
        payload = {
            "deviceSerial": device_serial,
            "sensorId": sensor_id,
            "startWhen": max(0, last_comms - MEASUREMENTS_WINDOW),
            "endWhen": last_comms,
            "maximumSegmentLength": 10,
            "startOffset": 0,
        }
        try:
            async with session.put(url, json=payload) as response:
                response.raise_for_status()
                data = await response.json(content_type=None)
                measurements = data.get("measurements", [])
                if measurements:
                    return measurements[-1].get("value")
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug(
                "Failed to fetch sensor %s for device %s: %s",
                sensor_id,
                device_serial,
                err,
            )
        return None

    async def _fetch_device_config(
        self,
        session: aiohttp.ClientSession,
        device_serial: int,
    ) -> dict[str, Any]:
        """Fetch device configuration properties."""
        url = f"http://{self.host}:{self.port}{API_CONFIG_PATH}"
        payload = {
            "deviceSerial": device_serial,
            "properties": CONFIG_PROPERTIES,
        }
        try:
            async with session.put(url, json=payload) as response:
                response.raise_for_status()
                data = await response.json(content_type=None)
                return {
                    prop["name"]: prop["value"]
                    for prop in data.get("properties", [])
                }
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug(
                "Failed to fetch config for device %s: %s", device_serial, err
            )
        return {}

    async def _enrich_device_status(
        self,
        session: aiohttp.ClientSession,
        status: dict[str, Any],
    ) -> None:
        """Enrich a device status dict with solar measurements and config."""
        device_serial = status.get("device")
        last_comms = status.get("lastComms", 0)
        if device_serial is None or last_comms <= 0:
            return

        solar_input, element_power, config = await asyncio.gather(
            self._fetch_sensor_measurement(
                session, device_serial, SENSOR_ID_SOLAR_INPUT, last_comms
            ),
            self._fetch_sensor_measurement(
                session, device_serial, SENSOR_ID_ELEMENT_POWER, last_comms
            ),
            self._fetch_device_config(session, device_serial),
            return_exceptions=True,
        )

        if not isinstance(solar_input, BaseException) and solar_input is not None:
            status["solarInput"] = solar_input
        if not isinstance(element_power, BaseException) and element_power is not None:
            status["elementPower"] = element_power
        if not isinstance(config, BaseException) and isinstance(config, dict):
            if "SolarSetPoint" in config:
                status["solarSetPoint"] = config["SolarSetPoint"]
            if "GridSetPoint" in config:
                status["gridSetPoint"] = config["GridSetPoint"]
            if "HeatingPolicy" in config:
                status["heatingPolicy"] = config["HeatingPolicy"]

    async def _async_update_data(self) -> list[dict[str, Any]]:
        """Fetch data from the Elon Smart Water device."""
        url = f"http://{self.host}:{self.port}{API_PATH}"
        try:
            async with async_timeout.timeout(API_TIMEOUT):
                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as response:
                        response.raise_for_status()
                        data = await response.json(content_type=None)
                        device_statuses = data.get("deviceStatuses", [])
                        await asyncio.gather(
                            *[
                                self._enrich_device_status(session, status)
                                for status in device_statuses
                            ],
                            return_exceptions=True,
                        )
                        return device_statuses
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
