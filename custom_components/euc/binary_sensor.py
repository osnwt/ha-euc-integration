from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, PROTOCOL_VETERAN
from .coordinator import EUCCoordinator


@dataclass(frozen=True, kw_only=True)
class EUCBinarySensorDescription(BinarySensorEntityDescription):
    value_key: str
    protocols: tuple[str, ...] | None = None


SENSORS: tuple[EUCBinarySensorDescription, ...] = (
    EUCBinarySensorDescription(
        key="charge_mode",
        translation_key="charge_mode",
        value_key="charge_mode",
        icon="mdi:battery-charging",
        entity_category=EntityCategory.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
        protocols=(PROTOCOL_VETERAN,),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EUCCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(EUCBinarySensor(coordinator, description) for description in SENSORS)


class EUCBinarySensor(CoordinatorEntity[EUCCoordinator], BinarySensorEntity):
    entity_description: EUCBinarySensorDescription

    def __init__(
        self,
        coordinator: EUCCoordinator,
        description: EUCBinarySensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{coordinator.address}_{description.key}"

    @property
    def device_info(self):
        return self.coordinator.device_info

    @property
    def is_on(self) -> bool | None:
        if self.coordinator.data is None:
            return None
        value = self.coordinator.data.get(self.entity_description.value_key)
        if value is None:
            return None
        return bool(value)

    @property
    def available(self) -> bool:
        if not self.coordinator.is_available or self.coordinator.data is None:
            return False
        if self.entity_description.protocols is None:
            return True
        return self.coordinator.data.get("protocol") in self.entity_description.protocols
