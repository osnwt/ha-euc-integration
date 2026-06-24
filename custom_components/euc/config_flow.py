from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_ADDRESS
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv

from .const import (
    BATTERY_PROFILES,
    BLE_SERVICE_UUID,
    CONF_BATTERY_PROFILE,
    DEFAULT_BATTERY_PROFILE,
    DOMAIN,
    NAME,
    PROTOCOL_BEGODE,
    PROTOCOL_VETERAN,
)


def _is_supported_discovery(info: BluetoothServiceInfoBleak) -> bool:
    name = (info.name or "").lower()
    if "sherman" in name or "leaper" in name or "lynx" in name or "begode" in name or "gotway" in name:
        return True

    service_uuids = {uuid.lower() for uuid in info.service_uuids}
    service_uuids.update(uuid.replace("-", "").lower() for uuid in info.service_uuids)
    target = BLE_SERVICE_UUID.lower()
    compact = target.replace("-", "")
    short = "ffe0"
    return target in service_uuids or compact in service_uuids or short in service_uuids


class EUCConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self,
        discovery_info: BluetoothServiceInfoBleak,
    ) -> FlowResult:
        if not _is_supported_discovery(discovery_info):
            return self.async_abort(reason="not_supported")

        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        assert self._discovery_info is not None

        if user_input is not None:
            return self.async_create_entry(
                title=self._discovery_info.name or f"{NAME} {self._discovery_info.address}",
                data={CONF_ADDRESS: self._discovery_info.address},
            )

        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self._discovery_info.name or NAME,
                "address": self._discovery_info.address,
            },
        )

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        discovered = await self._async_discovered_devices()
        if user_input is not None:
            manual_address = user_input.get("manual_address", "").strip()
            if manual_address:
                address = manual_address.upper()
                title = f"{NAME} {address}"
            else:
                address = user_input[CONF_ADDRESS]
                discovery_info = discovered[address]
                title = discovery_info.name or f"{NAME} {address}"

            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=title,
                data={CONF_ADDRESS: address},
            )

        schema_fields: dict[Any, Any] = {
            vol.Optional("manual_address"): cv.string,
        }
        if discovered:
            options = {
                address: f"{info.name or NAME} ({address})"
                for address, info in discovered.items()
            }
            schema_fields[vol.Optional(CONF_ADDRESS)] = vol.In(options)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(schema_fields),
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> "EUCOptionsFlow":
        return EUCOptionsFlow(config_entry)

    async def _async_discovered_devices(self) -> dict[str, BluetoothServiceInfoBleak]:
        configured = {entry.unique_id for entry in self._async_current_entries()}
        discovered: dict[str, BluetoothServiceInfoBleak] = {}
        for info in bluetooth.async_discovered_service_info(self.hass, connectable=True):
            if info.address in configured:
                continue
            if not _is_supported_discovery(info):
                continue
            discovered[info.address] = info
        return discovered


class EUCOptionsFlow(OptionsFlow):
    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        protocol = self._get_detected_protocol()
        if protocol == PROTOCOL_VETERAN:
            return self.async_abort(reason="no_configurable_options")

        current = self._config_entry.options.get(CONF_BATTERY_PROFILE, DEFAULT_BATTERY_PROFILE)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_BATTERY_PROFILE, default=current): vol.In(
                        {key: profile["label"] for key, profile in BATTERY_PROFILES.items()}
                    ),
                }
            ),
        )

    def _get_detected_protocol(self) -> str | None:
        coordinator = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id)
        if coordinator is None or coordinator.data is None:
            return None
        return coordinator.data.get("protocol")
