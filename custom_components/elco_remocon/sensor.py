"""Sensor entities for Elco Remocon-Net."""

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
from homeassistant.const import EntityCategory, UnitOfPressure, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import RemoconData
from .const import DOMAIN
from .coordinator import ElcoRemoconCoordinator


@dataclass(kw_only=True)
class ElcoSensorDescription(SensorEntityDescription):
    """Describe an Elco sensor entity."""

    key: str
    translation_key: str
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    native_unit_of_measurement: str | None = None
    entity_category: EntityCategory | None = None
    suggested_display_precision: int = 1
    value_fn: Callable[[RemoconData], StateType]
    exists_fn: Callable[[RemoconData], bool] = lambda _: True


SENSORS: tuple[ElcoSensorDescription, ...] = (
    ElcoSensorDescription(
        key="room_temperature",
        translation_key="room_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.room_temp if d.has_room_sensor else None,
        exists_fn=lambda d: d.has_room_sensor,
    ),
    ElcoSensorDescription(
        key="outside_temp",
        translation_key="outside_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.outside_temp,
    ),
    ElcoSensorDescription(
        key="zone_desired_temperature",
        translation_key="zone_desired_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.desired_temp if d.desired_temp > 0 else None,
    ),
    ElcoSensorDescription(
        key="system_pressure",
        translation_key="system_pressure",
        device_class=SensorDeviceClass.PRESSURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPressure.BAR,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.system_pressure,
        exists_fn=lambda d: d.system_pressure is not None,
    ),
    ElcoSensorDescription(
        key="dhw_storage_temperature",
        translation_key="dhw_storage_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.dhw_temp if d.dhw_temp > 0 else None,
        exists_fn=lambda d: d.dhw_enabled,
    ),
    ElcoSensorDescription(
        key="flow_setpoint_temp",
        translation_key="flow_setpoint_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.flow_setpoint_temperature,
        exists_fn=lambda d: d.flow_setpoint_temperature is not None,
    ),
    ElcoSensorDescription(
        key="error_text",
        translation_key="error_text",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.error_text,
        exists_fn=lambda d: d.error_text is not None,
    ),
    ElcoSensorDescription(
        key="quiet_mode_start",
        translation_key="quiet_mode_start",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.quiet_mode_start,
        exists_fn=lambda d: d.quiet_mode_start is not None,
    ),
    ElcoSensorDescription(
        key="quiet_mode_end",
        translation_key="quiet_mode_end",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.quiet_mode_end,
        exists_fn=lambda d: d.quiet_mode_end is not None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Elco sensors."""
    coordinator: ElcoRemoconCoordinator = hass.data[DOMAIN][entry.entry_id]
    gw_id = entry.data["gateway_id"]

    entities = [
        ElcoSensor(coordinator, gw_id, desc)
        for desc in SENSORS
        if desc.exists_fn(coordinator.data)
    ]
    async_add_entities(entities)


class ElcoSensor(CoordinatorEntity[ElcoRemoconCoordinator], SensorEntity):
    """Elco sensor entity."""

    _attr_has_entity_name = True
    entity_description: ElcoSensorDescription

    def __init__(
        self,
        coordinator: ElcoRemoconCoordinator,
        gw_id: str,
        description: ElcoSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{gw_id}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> StateType:
        """Return sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)
