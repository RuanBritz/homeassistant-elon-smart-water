"""Shared base entity for Elon Smart Water control entities."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ElonSmartWaterCoordinator


class ElonSmartWaterEntity(CoordinatorEntity[ElonSmartWaterCoordinator]):
    """Base entity bound to a single device reported by the controller."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: ElonSmartWaterCoordinator, device_id: str
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_id = device_id

    @property
    def _device_serial(self) -> int | None:
        """Return the integer device serial, or None if it isn't numeric."""
        try:
            return int(self._device_id)
        except (TypeError, ValueError):
            return None

    def _get_device_status(self) -> dict[str, Any] | None:
        """Return the current status dict for this device."""
        for status in self.coordinator.data or []:
            if str(status.get("device")) == self._device_id:
                return status
        return None

    @property
    def available(self) -> bool:
        """Entity is available while the controller still reports the device."""
        return super().available and self._get_device_status() is not None

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
