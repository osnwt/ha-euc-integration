from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_PERIODIC_UPDATES, DOMAIN
from .coordinator import EUCCoordinator


@dataclass(frozen=True, kw_only=True)
class EUCSwitchDescription(SwitchEntityDescription):
    pass


SWITCHES: tuple[EUCSwitchDescription, ...] = (
    EUCSwitchDescription(
        key="periodic_updates",
        translation_key="periodic_updates",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: EUCCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(EUCSwitch(coordinator, description) for description in SWITCHES)


class EUCSwitch(CoordinatorEntity[EUCCoordinator], SwitchEntity):
    entity_description: EUCSwitchDescription

    def __init__(self, coordinator: EUCCoordinator, description: EUCSwitchDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{coordinator.address}_{description.key}"

    @property
    def device_info(self):
        return self.coordinator.device_info

    @property
    def is_on(self) -> bool:
        return self.coordinator.periodic_updates

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_update_runtime_options(**{CONF_PERIODIC_UPDATES: True})

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_update_runtime_options(**{CONF_PERIODIC_UPDATES: False})
