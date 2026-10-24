"""HTTP client for Elon Smart Water grid reheat control.

Request shapes were confirmed against a capture of the official app. Each
control request is a JSON body carrying applicationId (int), authId (str) and
deviceSerial (int). The app gets authId from /V1/ApplicationVerification/
Authenticate; it looks like "<base64 timestamp>:<base64 signature>".

applicationId/authId default to 0/"" and can be set in the integration options.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
import async_timeout

from .const import API_TIMEOUT, PATH_CANCEL_GRID_HEATING, PATH_FORCE_REHEAT

_LOGGER = logging.getLogger(__name__)


class ElonApiError(Exception):
    """Raised when a control request fails."""


class ElonLocalClient:
    """Sends control requests to a thermostat."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        application_id: int = 0,
        auth_id: str = "",
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._base = f"http://{host}:{port}"
        self._application_id = application_id
        self._auth_id = auth_id

    def _auth_body(self, device_serial: int) -> dict[str, Any]:
        """Return the body shared by every device-scoped request."""
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
        if isinstance(data, dict) and data.get("status") not in (None, "Success"):
            raise ElonApiError(f"{path} returned status {data.get('status')!r}")
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
