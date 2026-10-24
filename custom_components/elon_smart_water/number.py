"""Number platform for Elon Smart Water (solar/grid setpoints)."""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import ElonApiError, ElonLocalClient
from .const import DOMAIN, MAX_SETPOINT, MIN_SETPOINT
from .coordinator import ElonSmartWaterCoordinator
from .entity import ElonSmartWaterEntity


@dataclass(frozen=True, kw_only=True)
class ElonNumberEntityDescription(NumberEntityDescription):
    """Describes an Elon Smart Water number entity."""

    value_key: str
    set_fn: Callable[[ElonLocalClient, int, float], Awaitable[object]]


NUMBER_DESCRIPTIONS: tuple[ElonNumberEntityDescription, ...] = (
    ElonNumberEntityDescription(
        key="solar_setpoint",
        name="Solar Setpoint",
        icon="mdi:thermometer-high",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_min_value=MIN_SETPOINT,
        native_max_value=MAX_SETPOINT,
        native_step=1,
        mode=NumberMode.BOX,
        value_key="solarSetPoint",
        set_fn=lambda client, serial, value: client.set_solar_setpoint(serial, value),
    ),
    ElonNumberEntityDescription(
        key="grid_setpoint",
        name="Grid Setpoint",
        icon="mdi:thermometer",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        native_min_value=MIN_SETPOINT,
        native_max_value=MAX_SETPOINT,
        native_step=1,
        mode=NumberMode.BOX,
        value_key="gridSetPoint",
        set_fn=lambda client, serial, value: client.set_grid_setpoint(serial, value),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Elon Smart Water number entities."""
    coordinator: ElonSmartWaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_devices: set[str] = set()

    @callback
    def _async_add_new_entities() -> None:
        new_entities: list[ElonSmartWaterNumber] = []
        for device_status in coordinator.data or []:
            device_id = str(device_status.get("device", "unknown"))
            if device_id not in known_devices:
                known_devices.add(device_id)
                for description in NUMBER_DESCRIPTIONS:
                    new_entities.append(
                        ElonSmartWaterNumber(coordinator, description, device_id)
                    )
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_entities))
    _async_add_new_entities()


class ElonSmartWaterNumber(ElonSmartWaterEntity, NumberEntity):
    """A writable temperature setpoint on the thermostat."""

    entity_description: ElonNumberEntityDescription

    def __init__(
        self,
        coordinator: ElonSmartWaterCoordinator,
        description: ElonNumberEntityDescription,
        device_id: str,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{description.key}"

    @property
    def native_value(self) -> float | None:
        """Return the current setpoint if the status reports it."""
        status = self._get_device_status()
        if status is None:
            return None
        value = status.get(self.entity_description.value_key)
        return float(value) if value is not None else None

    async def async_set_native_value(self, value: float) -> None:
        """Write a new setpoint to the device."""
        serial = self._device_serial
        if serial is None:
            raise HomeAssistantError(
                f"Device id {self._device_id} is not a numeric serial"
            )
        try:
            await self.entity_description.set_fn(
                self.coordinator.client, serial, value
            )
        except ElonApiError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
