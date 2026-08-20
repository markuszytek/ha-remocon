"""Select entities for Elco Remocon-Net."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.select import SelectEntity

from .const import DOMAIN
from .coordinator import ElcoRemoconCoordinator

PLANT_MODE_OPTIONS: dict[str, int] = {
    "Sommer (nur Brauchwasser)": 0,
    "Winter (Heizen und TWW)": 1,
    "Nur Heizung": 2,
    "Kühlen": 3,
    "AUS": 5,
}

DHW_MODE_OPTIONS: dict[str, int] = {
    "Deaktiviert": 0,
    "Zeitbasiert": 1,
    "Ständiger Betrieb": 2,
}

ZONE_MODE_OPTIONS: dict[str, int] = {
    "AUS": 0,
    "Handbetrieb": 2,
    "Zeitprogramm": 3,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Elco select entities."""
    coordinator: ElcoRemoconCoordinator = hass.data[DOMAIN][entry.entry_id]
    gateway_id = entry.data["gateway_id"]
    async_add_entities(
        [
            ElcoPlantModeSelect(coordinator, gateway_id),
            ElcoDhwModeSelect(coordinator, gateway_id),
            ElcoZoneModeSelect(coordinator, gateway_id),
        ]
    )


class ElcoPlantModeSelect(
    CoordinatorEntity[ElcoRemoconCoordinator], SelectEntity
):
    """Select the plant operation mode using human-readable options."""

    _attr_has_entity_name = True
    _attr_translation_key = "plant_mode"
    _attr_options = list(PLANT_MODE_OPTIONS)

    def __init__(self, coordinator: ElcoRemoconCoordinator, gateway_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{gateway_id}_plant_mode"
        self._attr_device_info = coordinator.device_info

    @property
    def current_option(self) -> str | None:
        """Return the current human-readable plant mode."""
        mode = self.coordinator.data.plant_mode
        return next(
            (option for option, value in PLANT_MODE_OPTIONS.items() if value == mode),
            None,
        )

    async def async_select_option(self, option: str) -> None:
        """Send the selected plant mode to the API."""
        mode = PLANT_MODE_OPTIONS.get(option)
        if mode is None:
            return
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_plant_mode, mode
        )
        await self.coordinator.async_request_refresh()


class ElcoDhwModeSelect(CoordinatorEntity[ElcoRemoconCoordinator], SelectEntity):
    """Select the domestic hot water operation mode."""

    _attr_has_entity_name = True
    _attr_translation_key = "dhw_mode"
    _attr_options = list(DHW_MODE_OPTIONS)

    def __init__(self, coordinator: ElcoRemoconCoordinator, gateway_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{gateway_id}_dhw_mode"
        self._attr_device_info = coordinator.device_info

    @property
    def current_option(self) -> str | None:
        """Return the current human-readable DHW mode."""
        mode = self.coordinator.data.dhw_mode
        return next(
            (option for option, value in DHW_MODE_OPTIONS.items() if value == mode),
            None,
        )

    async def async_select_option(self, option: str) -> None:
        """Send the selected DHW mode to the API."""
        mode = DHW_MODE_OPTIONS.get(option)
        if mode is None:
            return
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_dhw_mode, mode
        )
        await self.coordinator.async_request_refresh()


class ElcoZoneModeSelect(CoordinatorEntity[ElcoRemoconCoordinator], SelectEntity):
    """Select the zone operation mode."""

    _attr_has_entity_name = True
    _attr_translation_key = "zone_mode"
    _attr_options = list(ZONE_MODE_OPTIONS)

    def __init__(self, coordinator: ElcoRemoconCoordinator, gateway_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{gateway_id}_zone_mode"
        self._attr_device_info = coordinator.device_info

    @property
    def current_option(self) -> str | None:
        """Return the current human-readable zone mode."""
        raw_mode = {0: 0, 3: 2, 1: 3}.get(self.coordinator.data.zone_mode)
        return next(
            (option for option, value in ZONE_MODE_OPTIONS.items() if value == raw_mode),
            None,
        )

    async def async_select_option(self, option: str) -> None:
        """Send the selected zone mode to the API."""
        mode = ZONE_MODE_OPTIONS.get(option)
        if mode is None:
            return
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_zone_mode_value, mode
        )
        await self.coordinator.async_request_refresh()