from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfLength,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EUCCoordinator


@dataclass(frozen=True, kw_only=True)
class EUCSensorDescription(SensorEntityDescription):
    value_key: str


SENSORS: tuple[EUCSensorDescription, ...] = (
    EUCSensorDescription(
        key="voltage",
        translation_key="voltage",
        value_key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    EUCSensorDescription(
        key="speed",
        translation_key="speed",
        value_key="speed",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    EUCSensorDescription(
        key="trip_distance",
        translation_key="trip_distance",
        value_key="trip_distance",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
    ),
    EUCSensorDescription(
        key="total_distance",
        translation_key="total_distance",
        value_key="total_distance",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=3,
    ),
    EUCSensorDescription(
        key="phase_current",
        translation_key="phase_current",
        value_key="phase_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    EUCSensorDescription(
        key="temperature",
        translation_key="temperature",
        value_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    EUCSensorDescription(
        key="pitch_angle",
        translation_key="pitch_angle",
        value_key="pitch_angle",
        native_unit_of_measurement="deg",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    EUCSensorDescription(
        key="pwm",
        translation_key="pwm",
        value_key="pwm",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    EUCSensorDescription(
        key="auto_off_seconds",
        translation_key="auto_off_seconds",
        value_key="auto_off_seconds",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    EUCSensorDescription(
        key="charge_mode",
        translation_key="charge_mode",
        value_key="charge_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    EUCSensorDescription(
        key="speed_alert",
        translation_key="speed_alert",
        value_key="speed_alert",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=2,
    ),
    EUCSensorDescription(
        key="speed_tiltback",
        translation_key="speed_tiltback",
        value_key="speed_tiltback",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=2,
    ),
    EUCSensorDescription(
        key="firmware_version",
        translation_key="firmware_version",
        value_key="firmware_version",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    EUCSensorDescription(
        key="pedals_mode",
        translation_key="pedals_mode",
        value_key="pedals_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EUCCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(EUCSensor(coordinator, description) for description in SENSORS)


class EUCSensor(CoordinatorEntity[EUCCoordinator], SensorEntity):
    entity_description: EUCSensorDescription

    def __init__(
        self,
        coordinator: EUCCoordinator,
        description: EUCSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{coordinator.address}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.value_key)

    @property
    def available(self) -> bool:
        return self.coordinator.is_available and self.coordinator.data is not None
