"""Binary sensor platform for Elon Smart Water."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ElonSmartWaterCoordinator


@dataclass(frozen=True)
class ElonBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes an Elon Smart Water binary sensor entity."""

    value_key: str = ""


BINARY_SENSOR_DESCRIPTIONS: tuple[ElonBinarySensorEntityDescription, ...] = (
    ElonBinarySensorEntityDescription(
        key="has_open_alarms",
        name="Open Alarms",
        value_key="hasOpenAlarms",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    ElonBinarySensorEntityDescription(
        key="ac_not_present",
        name="AC Not Present",
        value_key="acNotPresent",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Elon Smart Water binary sensor entities."""
    coordinator: ElonSmartWaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_devices: set[str] = set()

    @callback
    def _async_add_new_entities() -> None:
        """Add binary sensor entities for any newly discovered devices."""
        new_entities: list[ElonSmartWaterBinarySensor] = []
        for device_status in coordinator.data or []:
            device_id = str(device_status.get("device", "unknown"))
            if device_id not in known_devices:
                known_devices.add(device_id)
                for description in BINARY_SENSOR_DESCRIPTIONS:
                    if description.value_key in device_status:
                        new_entities.append(
                            ElonSmartWaterBinarySensor(
                                coordinator, description, device_id
                            )
                        )
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_entities))
    _async_add_new_entities()


class ElonSmartWaterBinarySensor(
    CoordinatorEntity[ElonSmartWaterCoordinator], BinarySensorEntity
):
    """Representation of an Elon Smart Water binary sensor."""

    entity_description: ElonBinarySensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ElonSmartWaterCoordinator,
        description: ElonBinarySensorEntityDescription,
        device_id: str,
    ) -> None:
        """Initialize the binary sensor entity."""
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
            configuration_url=f"http://{self.coordinator.host}:{self.coordinator.port}",
            suggested_area=street_address,
        )

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        status = self._get_device_status()
        if status is None:
            return None
        return bool(status.get(self.entity_description.value_key))
