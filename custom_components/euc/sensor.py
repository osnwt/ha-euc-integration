from __future__ import annotations

from dataclasses import dataclass
from typing import Final

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
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
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

from .const import DOMAIN, PROTOCOL_VETERAN
from .coordinator import EUCCoordinator


@dataclass(frozen=True, kw_only=True)
class EUCSensorDescription(SensorEntityDescription):
    value_key: str
    protocols: tuple[str, ...] | None = None


VETERAN_ONLY: Final = (PROTOCOL_VETERAN,)


SENSORS: tuple[EUCSensorDescription, ...] = (
    EUCSensorDescription(
        key="battery_level",
        translation_key="battery_level",
        value_key="battery_level",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
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
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="pwm",
        translation_key="pwm",
        value_key="pwm",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="auto_off_seconds",
        translation_key="auto_off_seconds",
        value_key="auto_off_seconds",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        entity_category=EntityCategory.DIAGNOSTIC,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="charge_mode",
        translation_key="charge_mode",
        value_key="charge_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="speed_alert",
        translation_key="speed_alert",
        value_key="speed_alert",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=2,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="speed_tiltback",
        translation_key="speed_tiltback",
        value_key="speed_tiltback",
        device_class=SensorDeviceClass.SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=2,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="firmware_version",
        translation_key="firmware_version",
        value_key="firmware_version",
        entity_category=EntityCategory.DIAGNOSTIC,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="pedals_mode",
        translation_key="pedals_mode",
        value_key="pedals_mode",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    EUCSensorDescription(
        key="rssi",
        translation_key="rssi",
        value_key="rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=0,
    ),
    EUCSensorDescription(
        key="bms1_voltage",
        translation_key="bms1_voltage",
        value_key="bms1_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=3,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="bms1_current",
        translation_key="bms1_current",
        value_key="bms1_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=2,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="bms1_cell_min",
        translation_key="bms1_cell_min",
        value_key="bms1_cell_min",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=3,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="bms1_cell_max",
        translation_key="bms1_cell_max",
        value_key="bms1_cell_max",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=3,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="bms1_cell_diff",
        translation_key="bms1_cell_diff",
        value_key="bms1_cell_diff",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=3,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="bms1_cell_avg",
        translation_key="bms1_cell_avg",
        value_key="bms1_cell_avg",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=3,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="bms1_cell_count",
        translation_key="bms1_cell_count",
        value_key="bms1_cell_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="bms2_voltage",
        translation_key="bms2_voltage",
        value_key="bms2_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=3,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="bms2_current",
        translation_key="bms2_current",
        value_key="bms2_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=2,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="bms2_cell_min",
        translation_key="bms2_cell_min",
        value_key="bms2_cell_min",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=3,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="bms2_cell_max",
        translation_key="bms2_cell_max",
        value_key="bms2_cell_max",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=3,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="bms2_cell_diff",
        translation_key="bms2_cell_diff",
        value_key="bms2_cell_diff",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=3,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="bms2_cell_avg",
        translation_key="bms2_cell_avg",
        value_key="bms2_cell_avg",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        entity_category=EntityCategory.DIAGNOSTIC,
        suggested_display_precision=3,
        protocols=VETERAN_ONLY,
    ),
    EUCSensorDescription(
        key="bms2_cell_count",
        translation_key="bms2_cell_count",
        value_key="bms2_cell_count",
        entity_category=EntityCategory.DIAGNOSTIC,
        protocols=VETERAN_ONLY,
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

    @property
    def device_info(self):
        return self.coordinator.device_info

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get(self.entity_description.value_key)

    @property
    def available(self) -> bool:
        if not self.coordinator.is_available or self.coordinator.data is None:
            return False
        if self.entity_description.protocols is None:
            return True
        return self.coordinator.data.get("protocol") in self.entity_description.protocols
