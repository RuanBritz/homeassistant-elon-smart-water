"""Button platform for Elon Smart Water (boost / cancel grid heating)."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import ElonApiError, ElonLocalClient
from .const import DOMAIN
from .coordinator import ElonSmartWaterCoordinator
from .entity import ElonSmartWaterEntity


@dataclass(frozen=True, kw_only=True)
class ElonButtonEntityDescription(ButtonEntityDescription):
    """Describes an Elon Smart Water button entity."""

    press_fn: Callable[[ElonLocalClient, int], Awaitable[Any]]


BUTTON_DESCRIPTIONS: tuple[ElonButtonEntityDescription, ...] = (
    ElonButtonEntityDescription(
        key="force_reheat",
        name="Boost (Force Reheat)",
        icon="mdi:water-boiler",
        press_fn=lambda client, serial: client.force_reheat(serial),
    ),
    ElonButtonEntityDescription(
        key="cancel_grid_heating",
        name="Cancel Grid Heating",
        icon="mdi:water-boiler-off",
        press_fn=lambda client, serial: client.cancel_grid_heating(serial),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Elon Smart Water button entities."""
    coordinator: ElonSmartWaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_devices: set[str] = set()

    @callback
    def _async_add_new_entities() -> None:
        new_entities: list[ElonSmartWaterButton] = []
        for device_status in coordinator.data or []:
            device_id = str(device_status.get("device", "unknown"))
            if device_id not in known_devices:
                known_devices.add(device_id)
                for description in BUTTON_DESCRIPTIONS:
                    new_entities.append(
                        ElonSmartWaterButton(coordinator, description, device_id)
                    )
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_entities))
    _async_add_new_entities()


class ElonSmartWaterButton(ElonSmartWaterEntity, ButtonEntity):
    """A momentary action on the thermostat."""

    entity_description: ElonButtonEntityDescription

    def __init__(
        self,
        coordinator: ElonSmartWaterCoordinator,
        description: ElonButtonEntityDescription,
        device_id: str,
    ) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{description.key}"

    async def async_press(self) -> None:
        """Send the action to the device."""
        serial = self._device_serial
        if serial is None:
            raise HomeAssistantError(
                f"Device id {self._device_id} is not a numeric serial"
            )
        try:
            await self.entity_description.press_fn(self.coordinator.client, serial)
        except ElonApiError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
