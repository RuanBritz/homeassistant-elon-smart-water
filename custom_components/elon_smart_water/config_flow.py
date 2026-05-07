"""Config flow for Elon Smart Water integration."""
from __future__ import annotations

import asyncio
import ipaddress
import logging
from typing import Any

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    API_PATH,
    CONF_HOST,
    CONF_NETWORK,
    CONF_PORT,
    DEFAULT_PORT,
    DOMAIN,
    MAX_CONCURRENT_SCANS,
    SCAN_TIMEOUT,
)

_LOGGER = logging.getLogger(__name__)


async def _async_test_connection(host: str, port: int) -> dict[str, Any] | None:
    """Test connection to an Elon Smart Water device and return parsed data."""
    url = f"http://{host}:{port}{API_PATH}"
    try:
        async with async_timeout.timeout(SCAN_TIMEOUT):
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json(content_type=None)
    except Exception:
        pass
    return None


async def _async_scan_network(network: str, port: int) -> list[str]:
    """Scan a network CIDR for Elon Smart Water devices."""
    found: list[str] = []
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_SCANS)

    try:
        net = ipaddress.IPv4Network(network, strict=False)
    except ValueError:
        _LOGGER.warning("Invalid network CIDR: %s", network)
        return found

    async def _check_host(ip: str) -> None:
        async with semaphore:
            data = await _async_test_connection(ip, port)
            if data is not None and "deviceStatuses" in data:
                found.append(ip)

    await asyncio.gather(*[_check_host(str(ip)) for ip in net.hosts()])
    return found


class ElonSmartWaterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Elon Smart Water."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_hosts: list[str] = []
        self._scan_port: int = DEFAULT_PORT

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step – present a menu."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["manual", "scan"],
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle manual IP entry step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)

            data = await _async_test_connection(host, port)
            if data is not None:
                await self.async_set_unique_id(f"{DOMAIN}_{host}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Elon Smart Water ({host})",
                    data={CONF_HOST: host, CONF_PORT: port},
                )
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )

    async def async_step_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle network scan step – enter network CIDR to scan."""
        errors: dict[str, str] = {}

        default_network = "192.168.1.0/24"
        try:
            local_ip = self.hass.config.api.local_ip
            net = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
            default_network = str(net)
        except Exception:
            pass

        if user_input is not None:
            self._scan_port = user_input.get(CONF_PORT, DEFAULT_PORT)
            self._discovered_hosts = await _async_scan_network(
                user_input[CONF_NETWORK], self._scan_port
            )
            if not self._discovered_hosts:
                errors["base"] = "no_devices_found"
            else:
                return await self.async_step_scan_results()

        return self.async_show_form(
            step_id="scan",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NETWORK, default=default_network): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )

    async def async_step_scan_results(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle scan results step – select a discovered device."""
        if user_input is not None:
            host = user_input[CONF_HOST]
            await self.async_set_unique_id(f"{DOMAIN}_{host}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Elon Smart Water ({host})",
                data={CONF_HOST: host, CONF_PORT: self._scan_port},
            )

        return self.async_show_form(
            step_id="scan_results",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): vol.In(self._discovered_hosts),
                }
            ),
            description_placeholders={"count": str(len(self._discovered_hosts))},
        )
