"""Number entities for Elco Remocon-Net."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
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
    """Set up Elco number entities."""
    coordinator: ElcoRemoconCoordinator = hass.data[DOMAIN][entry.entry_id]
    gateway_id = entry.data["gateway_id"]
    async_add_entities(
        [
            ElcoZoneComfortTemperatureNumber(coordinator, gateway_id),
            ElcoZoneEconomyTemperatureNumber(coordinator, gateway_id),
            ElcoZoneCoolingComfortTemperatureNumber(coordinator, gateway_id),
            ElcoZoneCoolingEconomyTemperatureNumber(coordinator, gateway_id),
            ElcoDhwTemperatureNumber(coordinator, gateway_id),
            ElcoDhwComfortTemperatureNumber(coordinator, gateway_id),
            ElcoDhwEconomyTemperatureNumber(coordinator, gateway_id),
        ]
    )


class ElcoDhwNumberBase(CoordinatorEntity[ElcoRemoconCoordinator], NumberEntity):
    """Shared availability behavior for DHW number entities."""

    @property
    def available(self) -> bool:
        """Return whether the gateway reports DHW support."""
        return super().available and self.coordinator.data.dhw_enabled


class ElcoDhwTemperatureNumber(
    ElcoDhwNumberBase
):
    """Set the domestic hot water target temperature."""

    _attr_has_entity_name = True
    _attr_translation_key = "dhw_target_temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = "slider"

    def __init__(self, coordinator: ElcoRemoconCoordinator, gateway_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{gateway_id}_dhw_target_temperature"
        self._attr_device_info = coordinator.device_info
        self._attr_native_min_value = 35
        self._attr_native_max_value = 65
        self._attr_native_step = 1

    @property
    def native_value(self) -> float:
        """Return the current DHW target temperature."""
        return self.coordinator.data.dhw_target_temp

    async def async_set_native_value(self, value: float) -> None:
        """Set a new DHW target temperature."""
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_dhw_temperature, value
        )
        await self.coordinator.async_request_refresh()


class ElcoDhwComfortTemperatureNumber(
    ElcoDhwNumberBase
):
    """Set the domestic hot water comfort temperature."""

    _attr_has_entity_name = True
    _attr_translation_key = "dhw_comfort_temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = "slider"
    _attr_native_min_value = 35
    _attr_native_max_value = 65
    _attr_native_step = 1

    def __init__(self, coordinator: ElcoRemoconCoordinator, gateway_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{gateway_id}_dhw_comfort_temperature"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float:
        """Return the current DHW comfort temperature."""
        return self.coordinator.data.dhw_comfort_temp

    async def async_set_native_value(self, value: float) -> None:
        """Set a new DHW comfort temperature."""
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_dhw_comfort_temperature, value
        )
        await self.coordinator.async_request_refresh()


class ElcoDhwEconomyTemperatureNumber(
    ElcoDhwNumberBase
):
    """Set the domestic hot water economy temperature."""

    _attr_has_entity_name = True
    _attr_translation_key = "dhw_reduced_temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = "slider"
    _attr_native_min_value = 35
    _attr_native_max_value = 48
    _attr_native_step = 1

    def __init__(self, coordinator: ElcoRemoconCoordinator, gateway_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{gateway_id}_dhw_reduced_temperature"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float:
        """Return the current DHW economy temperature."""
        return self.coordinator.data.dhw_reduced_temp

    async def async_set_native_value(self, value: float) -> None:
        """Set a new DHW economy temperature."""
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_dhw_economy_temperature, value
        )
        await self.coordinator.async_request_refresh()


class ElcoZoneComfortTemperatureNumber(
    CoordinatorEntity[ElcoRemoconCoordinator], NumberEntity
):
    """Set the zone comfort temperature."""

    _attr_has_entity_name = True
    _attr_translation_key = "comfort_temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = "slider"
    _attr_native_min_value = 10
    _attr_native_max_value = 30
    _attr_native_step = 0.5

    def __init__(self, coordinator: ElcoRemoconCoordinator, gateway_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{gateway_id}_zone_comfort_temperature"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float:
        """Return the current zone comfort temperature."""
        return self.coordinator.data.comfort_temp

    async def async_set_native_value(self, value: float) -> None:
        """Set a new zone comfort temperature."""
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_zone_comfort_temperature, value
        )
        await self.coordinator.async_request_refresh()


class ElcoZoneEconomyTemperatureNumber(
    CoordinatorEntity[ElcoRemoconCoordinator], NumberEntity
):
    """Set the zone economy temperature."""

    _attr_has_entity_name = True
    _attr_translation_key = "reduced_temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = "slider"
    _attr_native_min_value = 10
    _attr_native_max_value = 30
    _attr_native_step = 0.5

    def __init__(self, coordinator: ElcoRemoconCoordinator, gateway_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{gateway_id}_zone_economy_temperature"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float:
        """Return the current zone economy temperature."""
        return self.coordinator.data.reduced_temp

    async def async_set_native_value(self, value: float) -> None:
        """Set a new zone economy temperature."""
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_zone_economy_temperature, value
        )
        await self.coordinator.async_request_refresh()


class ElcoZoneCoolingComfortTemperatureNumber(
    CoordinatorEntity[ElcoRemoconCoordinator], NumberEntity
):
    """Set the zone cooling comfort temperature."""

    _attr_has_entity_name = True
    _attr_translation_key = "cooling_comfort_temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = "slider"
    _attr_native_min_value = 10
    _attr_native_max_value = 30
    _attr_native_step = 0.5

    def __init__(self, coordinator: ElcoRemoconCoordinator, gateway_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{gateway_id}_zone_cooling_comfort_temperature"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float:
        """Return the current zone cooling comfort temperature."""
        return self.coordinator.data.cooling_comfort_temp

    async def async_set_native_value(self, value: float) -> None:
        """Set a new zone cooling comfort temperature."""
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_zone_cooling_comfort_temperature, value
        )
        await self.coordinator.async_request_refresh()


class ElcoZoneCoolingEconomyTemperatureNumber(
    CoordinatorEntity[ElcoRemoconCoordinator], NumberEntity
):
    """Set the zone cooling economy temperature."""

    _attr_has_entity_name = True
    _attr_translation_key = "cooling_reduced_temperature"
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_mode = "slider"
    _attr_native_min_value = 10
    _attr_native_max_value = 30
    _attr_native_step = 0.5

    def __init__(self, coordinator: ElcoRemoconCoordinator, gateway_id: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{gateway_id}_zone_cooling_economy_temperature"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float:
        """Return the current zone cooling economy temperature."""
        return self.coordinator.data.cooling_reduced_temp

    async def async_set_native_value(self, value: float) -> None:
        """Set a new zone cooling economy temperature."""
        await self.hass.async_add_executor_job(
            self.coordinator.client.set_zone_cooling_economy_temperature, value
        )
        await self.coordinator.async_request_refresh()