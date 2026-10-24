"""Select platform for Elon Smart Water (heating policy)."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import ElonApiError
from .const import DOMAIN, HEATING_POLICY_OPTIONS
from .coordinator import ElonSmartWaterCoordinator
from .entity import ElonSmartWaterEntity

# Reverse map: device integer -> option label.
_VALUE_TO_LABEL: dict[int, str] = {v: k for k, v in HEATING_POLICY_OPTIONS.items()}

DESCRIPTION = SelectEntityDescription(
    key="heating_policy",
    name="Heating Policy",
    icon="mdi:solar-power-variant",
    options=list(HEATING_POLICY_OPTIONS),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the heating policy select entity per device."""
    coordinator: ElonSmartWaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_devices: set[str] = set()

    @callback
    def _async_add_new_entities() -> None:
        new_entities: list[ElonHeatingPolicySelect] = []
        for device_status in coordinator.data or []:
            device_id = str(device_status.get("device", "unknown"))
            if device_id not in known_devices:
                known_devices.add(device_id)
                new_entities.append(ElonHeatingPolicySelect(coordinator, device_id))
        if new_entities:
            async_add_entities(new_entities)

    entry.async_on_unload(coordinator.async_add_listener(_async_add_new_entities))
    _async_add_new_entities()


class ElonHeatingPolicySelect(ElonSmartWaterEntity, SelectEntity):
    """Selects the device heating policy (Solar Only / Grid Only)."""

    entity_description = DESCRIPTION

    def __init__(
        self, coordinator: ElonSmartWaterCoordinator, device_id: str
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{DESCRIPTION.key}"

    @property
    def current_option(self) -> str | None:
        """Return the current policy if the status reports one."""
        status = self._get_device_status()
        if status is None:
            return None
        # The status payload may expose the policy under a few possible keys.
        for key in ("heatingPolicy", "configuredPolicy", "heating_policy"):
            if key in status:
                return _VALUE_TO_LABEL.get(status[key])
        return None

    async def async_select_option(self, option: str) -> None:
        """Change the heating policy on the device."""
        serial = self._device_serial
        if serial is None:
            raise HomeAssistantError(
                f"Device id {self._device_id} is not a numeric serial"
            )
        policy = HEATING_POLICY_OPTIONS[option]
        try:
            await self.coordinator.client.set_heating_policy(serial, policy)
        except ElonApiError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
