from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CONNECTED_SECONDS,
    CONF_DISCONNECTED_SECONDS,
    DOMAIN,
    MAX_CONNECTED_SECONDS,
    MAX_DISCONNECTED_SECONDS,
    MIN_CONNECTED_SECONDS,
    MIN_DISCONNECTED_SECONDS,
)
from .coordinator import EUCCoordinator


@dataclass(frozen=True, kw_only=True)
class EUCNumberDescription(NumberEntityDescription):
    option_key: str
    minimum: float
    maximum: float


NUMBERS: tuple[EUCNumberDescription, ...] = (
    EUCNumberDescription(
        key="connected_seconds",
        translation_key="connected_seconds",
        option_key=CONF_CONNECTED_SECONDS,
        native_min_value=MIN_CONNECTED_SECONDS,
        native_max_value=MAX_CONNECTED_SECONDS,
        minimum=MIN_CONNECTED_SECONDS,
        maximum=MAX_CONNECTED_SECONDS,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
    ),
    EUCNumberDescription(
        key="disconnected_seconds",
        translation_key="disconnected_seconds",
        option_key=CONF_DISCONNECTED_SECONDS,
        native_min_value=MIN_DISCONNECTED_SECONDS,
        native_max_value=MAX_DISCONNECTED_SECONDS,
        minimum=MIN_DISCONNECTED_SECONDS,
        maximum=MAX_DISCONNECTED_SECONDS,
        native_step=1,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EUCCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(EUCNumber(coordinator, description) for description in NUMBERS)


class EUCNumber(CoordinatorEntity[EUCCoordinator], NumberEntity):
    entity_description: EUCNumberDescription

    def __init__(self, coordinator: EUCCoordinator, description: EUCNumberDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{coordinator.address}_{description.key}"

    @property
    def device_info(self):
        return self.coordinator.device_info

    @property
    def native_value(self) -> float:
        if self.entity_description.option_key == CONF_CONNECTED_SECONDS:
            return float(self.coordinator.connected_seconds)
        return float(self.coordinator.disconnected_seconds)

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_update_runtime_options(
            **{self.entity_description.option_key: int(value)}
        )
