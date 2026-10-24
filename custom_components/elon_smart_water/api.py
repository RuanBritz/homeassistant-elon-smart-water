"""Local HTTP client for controlling an Elon Smart Water thermostat.

The thermostat exposes an HTTP API on port 80. Request/response shapes here were
recovered from the app's compiled Dart (libapp.so); see API_ENDPOINTS.md. Every
control request is a JSON body carrying applicationId, authId and deviceSerial as
integers, which the app obtains from an on-device pairing handshake.

Status reads on the local port work with no auth, so applicationId/authId default
to 0. If a device rejects unauthenticated control, the user can supply the values
captured from the app via the integration options.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import async_timeout

from .const import (
    API_TIMEOUT,
    PATH_CANCEL_GRID_HEATING,
    PATH_FORCE_REHEAT,
    PATH_PROPERTY_QUERY,
    PATH_PROPERTY_UPDATE,
    PROP_GRID_SETPOINT,
    PROP_HEATING_POLICY,
    PROP_SOLAR_SETPOINT,
)

_LOGGER = logging.getLogger(__name__)


class ElonApiError(Exception):
    """Raised when a local control request fails."""


class ElonLocalClient:
    """Sends control requests to a thermostat on the local network."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        application_id: int = 0,
        auth_id: int = 0,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._base = f"http://{host}:{port}"
        self._application_id = application_id
        self._auth_id = auth_id

    def _auth_body(self, device_serial: int) -> dict[str, Any]:
        """Return the base body shared by every device-scoped request."""
        return {
            "applicationId": self._application_id,
            "authId": self._auth_id,
            "deviceSerial": device_serial,
        }

    async def _request(
        self, method: str, path: str, body: dict[str, Any]
    ) -> dict[str, Any]:
        """Send one request and return the decoded JSON response."""
        url = f"{self._base}{path}"
        try:
            async with async_timeout.timeout(API_TIMEOUT):
                async with self._session.request(
                    method,
                    url,
                    json=body,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                ) as response:
                    response.raise_for_status()
                    data = await response.json(content_type=None)
        except asyncio.TimeoutError as err:
            raise ElonApiError(f"Timeout calling {path} on {url}") from err
        except aiohttp.ClientError as err:
            raise ElonApiError(f"Error calling {path} on {url}: {err}") from err
        return data if isinstance(data, dict) else {"data": data}

    async def force_reheat(self, device_serial: int) -> dict[str, Any]:
        """Force a grid reheat (the app's 'boost' / 'heat now')."""
        return await self._request(
            "PUT", PATH_FORCE_REHEAT, self._auth_body(device_serial)
        )

    async def cancel_grid_heating(self, device_serial: int) -> dict[str, Any]:
        """Cancel an in-progress grid heating cycle."""
        return await self._request(
            "PUT", PATH_CANCEL_GRID_HEATING, self._auth_body(device_serial)
        )

    async def set_property(
        self, device_serial: int, name: str, value: Any
    ) -> dict[str, Any]:
        """Update a single device configuration property."""
        body = self._auth_body(device_serial)
        body["name"] = name
        body["value"] = value
        return await self._request("PUT", PATH_PROPERTY_UPDATE, body)

    async def set_heating_policy(
        self, device_serial: int, policy: int
    ) -> dict[str, Any]:
        """Set the heating policy (1 = Solar Only, 5 = Grid Only)."""
        return await self.set_property(device_serial, PROP_HEATING_POLICY, policy)

    async def set_solar_setpoint(
        self, device_serial: int, temperature: float
    ) -> dict[str, Any]:
        """Set the solar target temperature (deg C)."""
        return await self.set_property(
            device_serial, PROP_SOLAR_SETPOINT, temperature
        )

    async def set_grid_setpoint(
        self, device_serial: int, temperature: float
    ) -> dict[str, Any]:
        """Set the grid target temperature (deg C)."""
        return await self.set_property(
            device_serial, PROP_GRID_SETPOINT, temperature
        )

    async def query_properties(
        self, device_serial: int, properties: list[str]
    ) -> dict[str, Any]:
        """Read one or more device configuration properties."""
        body = self._auth_body(device_serial)
        body["properties"] = properties
        return await self._request("PUT", PATH_PROPERTY_QUERY, body)
