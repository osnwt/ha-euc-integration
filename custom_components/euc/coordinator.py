from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .ble import EUCBleClient
from .const import (
    BEGODE_ONLY_SENSOR_KEYS,
    CONF_BATTERY_PROFILE,
    DEFAULT_BATTERY_PROFILE,
    DOMAIN,
    EVENT_EUC_CONNECTED,
    EVENT_EUC_DISCONNECTED,
    MODEL_UNKNOWN,
    NAME,
    PROTOCOL_BEGODE,
    PROTOCOL_VETERAN,
    REMOVED_SENSOR_KEYS,
    STALE_AFTER,
    VETERAN_ONLY_SENSOR_KEYS,
    VENDOR_UNKNOWN,
)
from .parser import TelemetrySample

_LOGGER = logging.getLogger(__name__)


class EUCCoordinator(DataUpdateCoordinator[TelemetrySample | None]):
    """Hold latest telemetry and connection state for one wheel."""

    def __init__(self, hass, entry) -> None:
        super().__init__(hass, logger=_LOGGER, name=NAME)
        self.config_entry = entry
        self.address: str = entry.unique_id or entry.data["address"]
        self.connected = False
        self.last_seen: datetime | None = None
        self._connect_event_sent = False
        self._started = False
        self._manufacturer = VENDOR_UNKNOWN
        self._model = MODEL_UNKNOWN
        self._device_registry_synced = False
        self._protocol_entities_pruned = False
        self.client = EUCBleClient(
            hass=hass,
            address=self.address,
            on_sample=self._handle_sample,
            on_availability_changed=self._handle_availability_changed,
            battery_profile=entry.options.get(CONF_BATTERY_PROFILE, DEFAULT_BATTERY_PROFILE),
        )
        self.data = None

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.address)},
            connections={(CONNECTION_BLUETOOTH, self.address)},
            name=self.config_entry.title or NAME,
            manufacturer=self._manufacturer,
            model=self._model,
        )

    async def async_start(self) -> None:
        if self._started:
            return
        self._started = True
        _LOGGER.info("EUC coordinator start: address=%s", self.address)
        await self.client.start()

    async def async_stop(self) -> None:
        self._started = False
        _LOGGER.info("EUC coordinator stop: address=%s", self.address)
        await self.client.stop()

    @property
    def is_available(self) -> bool:
        if not self.connected or self.last_seen is None:
            return False
        return datetime.now(UTC) - self.last_seen <= STALE_AFTER

    def _event_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "entry_id": self.config_entry.entry_id,
            "address": self.address,
            "name": self.config_entry.title or NAME,
            "vendor": self._manufacturer,
            "model": self._model,
            "protocol": self.data.get("protocol") if self.data else "unknown",
        }
        if self.last_seen is not None:
            payload["last_seen"] = self.last_seen.isoformat()
        if self.data is not None:
            payload["sample"] = dict(self.data)
        return payload

    def _handle_sample(self, sample: TelemetrySample) -> None:
        previous_manufacturer = self._manufacturer
        previous_model = self._model
        self._manufacturer = sample.get("vendor", VENDOR_UNKNOWN)
        self._model = sample.get("model", MODEL_UNKNOWN)
        self.connected = True
        self.last_seen = datetime.now(UTC)
        self.async_set_updated_data(sample)
        if (
            not self._device_registry_synced
            or previous_manufacturer != self._manufacturer
            or previous_model != self._model
        ):
            self._device_registry_synced = True
            self.hass.async_create_background_task(
                self._async_update_device_registry(),
                f"euc_device_registry_{self.address}",
            )
        protocol = sample.get("protocol")
        if protocol is not None and not self._protocol_entities_pruned:
            self._protocol_entities_pruned = True
            self.hass.async_create_background_task(
                self._async_prune_protocol_entities(protocol),
                f"euc_entity_prune_{self.address}",
            )

        if not self._connect_event_sent:
            _LOGGER.info("EUC first sample: address=%s sample=%s", self.address, sample)
            self._connect_event_sent = True
            self.hass.bus.async_fire(EVENT_EUC_CONNECTED, self._event_payload())

    def _handle_availability_changed(self, available: bool) -> None:
        was_connected = self.connected
        self.connected = available and self.last_seen is not None
        _LOGGER.info(
            "EUC availability changed: address=%s available=%s last_seen=%s",
            self.address,
            available,
            self.last_seen.isoformat() if self.last_seen else None,
        )
        if not available and was_connected and self._connect_event_sent:
            self._connect_event_sent = False
            self.hass.bus.async_fire(EVENT_EUC_DISCONNECTED, self._event_payload())
        self.async_update_listeners()

    async def _async_update_data(self) -> TelemetrySample | None:
        return self.data

    async def _async_update_device_registry(self) -> None:
        registry = dr.async_get(self.hass)
        device = registry.async_get_device(
            identifiers={(DOMAIN, self.address)},
            connections={(CONNECTION_BLUETOOTH, self.address)},
        )
        if device is None:
            return
        registry.async_update_device(
            device.id,
            manufacturer=self._manufacturer,
            model=self._model,
        )

    async def _async_prune_protocol_entities(self, protocol: str) -> None:
        if protocol == PROTOCOL_VETERAN:
            incompatible_keys = BEGODE_ONLY_SENSOR_KEYS
        elif protocol == PROTOCOL_BEGODE:
            incompatible_keys = VETERAN_ONLY_SENSOR_KEYS
        else:
            return

        registry = er.async_get(self.hass)
        entries = er.async_entries_for_config_entry(registry, self.config_entry.entry_id)
        for entry in entries:
            if not entry.unique_id.startswith(f"{self.address}_"):
                continue
            sensor_key = entry.unique_id.removeprefix(f"{self.address}_")
            if sensor_key not in incompatible_keys and sensor_key not in REMOVED_SENSOR_KEYS:
                continue
            _LOGGER.info(
                "EUC removing incompatible entity: address=%s protocol=%s unique_id=%s",
                self.address,
                protocol,
                entry.unique_id,
            )
            registry.async_remove(entry.entity_id)
