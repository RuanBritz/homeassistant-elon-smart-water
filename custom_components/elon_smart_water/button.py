"""Button platform for Elon Smart Water."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import (
    ButtonEntity,
    ButtonEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    API_CANCEL_GRID_HEATING_PATH,
    API_FORCE_REHEAT_PATH,
    DOMAIN,
)
from .coordinator import ElonSmartWaterCoordinator


@dataclass(frozen=True)
class ElonButtonEntityDescription(ButtonEntityDescription):
    """Describes an Elon Smart Water button entity."""

    command_path: str = ""


BUTTON_DESCRIPTIONS: tuple[ElonButtonEntityDescription, ...] = (
    ElonButtonEntityDescription(
        key="force_reheat",
        name="Force Reheat",
        icon="mdi:fire",
        command_path=API_FORCE_REHEAT_PATH,
    ),
    ElonButtonEntityDescription(
        key="cancel_grid_heating",
        name="Cancel Grid Heating",
        icon="mdi:power-plug-off",
        command_path=API_CANCEL_GRID_HEATING_PATH,
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
        """Add button entities for any newly discovered devices."""
        new_entities: list[ElonSmartWaterButton] = []
        for device_status in coordinator.data or []:
            device_id = str(device_status.get("device", ""))
            if not device_id or device_id in known_devices:
                continue

            known_devices.add(device_id)
            for description in BUTTON_DESCRIPTIONS:
                new_entities.append(
                    ElonSmartWaterButton(coordinator, description, device_id)
                )

        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_entities))
    _async_add_new_entities()


class ElonSmartWaterButton(
    CoordinatorEntity[ElonSmartWaterCoordinator], ButtonEntity
):
    """Representation of an Elon Smart Water button."""

    entity_description: ElonButtonEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ElonSmartWaterCoordinator,
        description: ElonButtonEntityDescription,
        device_id: str,
    ) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)
        self.entity_description = description
        self._device_id = device_id
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{description.key}"

    def _get_device_status(self) -> dict[str, Any] | None:
        """Return the current status dict for this device."""
        for status in self.coordinator.data or []:
            if str(status.get("device")) == self._device_id:
                return status
        return None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the device registry."""
        status = self._get_device_status()
        name = (
            status.get("logicalName", f"Elon Water Heater {self._device_id}")
            if status
            else f"Elon Water Heater {self._device_id}"
        )
        street_address = status.get("streetAddress") if status else None
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=name,
            manufacturer="Elon",
            model="Smart Water Heater",
            configuration_url=(
                f"http://{self.coordinator.host}:{self.coordinator.port}"
            ),
            suggested_area=street_address,
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        try:
            device_serial = int(self._device_id)
        except ValueError as err:
            raise HomeAssistantError(
                f"Invalid device serial for command: {self._device_id}"
            ) from err

        await self.coordinator.async_send_thermostat_command(
            self.entity_description.command_path,
            device_serial,
        )
        await self.coordinator.async_request_refresh()
