"""Switch entities for Elco Remocon-Net."""

from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ElcoRemoconCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Elco switch entities."""
    coordinator: ElcoRemoconCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [ElcoAutomaticThermoregulationSwitch(coordinator, entry.data["gateway_id"])]
    )


class ElcoAutomaticThermoregulationSwitch(
    CoordinatorEntity[ElcoRemoconCoordinator], SwitchEntity
):
    """Control automatic thermoregulation."""

    _attr_has_entity_name = True
    _attr_translation_key = "automatic_thermoregulation"

    def __init__(self, coordinator: ElcoRemoconCoordinator, gateway_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{gateway_id}_automatic_thermoregulation"
        self._attr_device_info = coordinator.device_info

    @property
    def is_on(self) -> bool:
        """Return whether automatic thermoregulation is enabled."""
        return self.coordinator.data.automatic_thermoregulation

    async def async_turn_on(self, **kwargs) -> None:
        """Enable automatic thermoregulation."""
        await self._async_set_enabled(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Disable automatic thermoregulation."""
        await self._async_set_enabled(False)

    async def _async_set_enabled(self, enabled: bool) -> None:
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_automatic_thermoregulation, enabled
        )
        await self.coordinator.async_request_refresh()