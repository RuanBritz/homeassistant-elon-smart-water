"""Sensor platform for Elon Smart Water."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ElonSmartWaterCoordinator


@dataclass(frozen=True)
class ElonSensorEntityDescription(SensorEntityDescription):
    """Describes an Elon Smart Water sensor entity."""

    value_key: str = ""
    value_fn: Callable[[Any], Any] | None = None


SENSOR_DESCRIPTIONS: tuple[ElonSensorEntityDescription, ...] = (
    ElonSensorEntityDescription(
        key="water_temperature",
        name="Water Temperature",
        value_key="waterTemperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ElonSensorEntityDescription(
        key="power_source",
        name="Power Source",
        value_key="powerSource",
    ),
    ElonSensorEntityDescription(
        key="reheat_time",
        name="Reheat Time",
        value_key="reheatTime",
        native_unit_of_measurement="min",
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ElonSensorEntityDescription(
        key="last_comms",
        name="Last Communication",
        value_key="lastComms",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Elon Smart Water sensor entities."""
    coordinator: ElonSmartWaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_devices: set[str] = set()

    @callback
    def _async_add_new_entities() -> None:
        """Add sensor entities for any newly discovered devices."""
        new_entities: list[ElonSmartWaterSensor] = []
        for device_status in coordinator.data or []:
            device_id = str(device_status.get("device", "unknown"))
            if device_id not in known_devices:
                known_devices.add(device_id)
                for description in SENSOR_DESCRIPTIONS:
                    if description.value_key in device_status:
                        new_entities.append(
                            ElonSmartWaterSensor(coordinator, description, device_id)
                        )
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_entities))
    _async_add_new_entities()


class ElonSmartWaterSensor(CoordinatorEntity[ElonSmartWaterCoordinator], SensorEntity):
    """Representation of an Elon Smart Water sensor."""

    entity_description: ElonSensorEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: ElonSmartWaterCoordinator,
        description: ElonSensorEntityDescription,
        device_id: str,
    ) -> None:
        """Initialize the sensor entity."""
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
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        status = self._get_device_status()
        if status is None:
            return None
        value = status.get(self.entity_description.value_key)
        if self.entity_description.value_fn is not None:
            return self.entity_description.value_fn(value)
        return value
