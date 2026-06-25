from __future__ import annotations

import asyncio
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
    CONF_CONNECTED_SECONDS,
    CONF_DISCONNECTED_SECONDS,
    CONF_PERIODIC_UPDATES,
    CONNECTION_STATE_CONNECTED,
    CONNECTION_STATE_COOLDOWN,
    CONNECTION_STATE_DISCONNECTED,
    DEFAULT_CONNECTED_SECONDS,
    DEFAULT_DISCONNECTED_SECONDS,
    DEFAULT_BATTERY_PROFILE,
    DEFAULT_PERIODIC_UPDATES,
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
        self._last_sample_seen: datetime | None = None
        self.connection_state = CONNECTION_STATE_DISCONNECTED
        self._connect_event_sent = False
        self._started = False
        self._manufacturer = VENDOR_UNKNOWN
        self._model = MODEL_UNKNOWN
        self._device_registry_synced = False
        self._protocol_entities_pruned = False
        self._periodic_updates = entry.options.get(CONF_PERIODIC_UPDATES, DEFAULT_PERIODIC_UPDATES)
        self._connected_seconds = entry.options.get(CONF_CONNECTED_SECONDS, DEFAULT_CONNECTED_SECONDS)
        self._disconnected_seconds = entry.options.get(
            CONF_DISCONNECTED_SECONDS, DEFAULT_DISCONNECTED_SECONDS
        )
        self._connected_task: asyncio.Task[None] | None = None
        self._cooldown_task: asyncio.Task[None] | None = None
        self._planned_disconnect = False
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
        self._cancel_timers()
        _LOGGER.info("EUC coordinator stop: address=%s", self.address)
        await self.client.stop()

    @property
    def is_available(self) -> bool:
        if not self.connected or self._last_sample_seen is None:
            return False
        return datetime.now(UTC) - self._last_sample_seen <= STALE_AFTER

    @property
    def periodic_updates(self) -> bool:
        return self._periodic_updates

    @property
    def connected_seconds(self) -> int:
        return self._connected_seconds

    @property
    def disconnected_seconds(self) -> int:
        return self._disconnected_seconds

    def telemetry_available(self, protocols: tuple[str, ...] | None = None) -> bool:
        if self.data is None:
            return False
        if protocols is not None and self.data.get("protocol") not in protocols:
            return False
        if self.connection_state == CONNECTION_STATE_COOLDOWN:
            return True
        return self.is_available

    def _set_connection_state(self, state: str) -> None:
        self.connection_state = state

    def _event_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "entry_id": self.config_entry.entry_id,
            "address": self.address,
            "name": self.config_entry.title or NAME,
            "vendor": self._manufacturer,
            "model": self._model,
            "connection_state": self.connection_state,
            "protocol": self.data.get("protocol") if self.data else "unknown",
        }
        if self._last_sample_seen is not None:
            payload["last_seen"] = self._last_sample_seen.isoformat()
        if self.data is not None:
            payload["sample"] = dict(self.data)
        return payload

    def _handle_sample(self, sample: TelemetrySample) -> None:
        previous_connection_state = self.connection_state
        previous_manufacturer = self._manufacturer
        previous_model = self._model
        now = datetime.now(UTC)
        self._manufacturer = sample.get("vendor", VENDOR_UNKNOWN)
        self._model = sample.get("model", MODEL_UNKNOWN)
        self.connected = True
        self._last_sample_seen = now
        if previous_connection_state != CONNECTION_STATE_CONNECTED:
            self._planned_disconnect = False
        self._cancel_cooldown_task()
        self._set_connection_state(CONNECTION_STATE_CONNECTED)
        self.async_set_updated_data(sample)
        if self._periodic_updates and previous_connection_state != CONNECTION_STATE_CONNECTED:
            self._schedule_connected_window()
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
        self.connected = available and self._last_sample_seen is not None
        _LOGGER.info(
            "EUC availability changed: address=%s available=%s last_seen=%s",
            self.address,
            available,
            self._last_sample_seen.isoformat() if self._last_sample_seen else None,
        )
        if not available:
            if self._planned_disconnect and self._periodic_updates and self.data is not None:
                self._planned_disconnect = False
                self._set_connection_state(CONNECTION_STATE_COOLDOWN)
                self._cancel_connected_task()
                self._schedule_cooldown()
            else:
                self._planned_disconnect = False
                self._cancel_timers()
                self._set_connection_state(CONNECTION_STATE_DISCONNECTED)
                self.async_set_updated_data(None)

            if was_connected and self._connect_event_sent:
                self._connect_event_sent = False
                self.hass.bus.async_fire(EVENT_EUC_DISCONNECTED, self._event_payload())
        self.async_update_listeners()

    async def _async_update_data(self) -> TelemetrySample | None:
        return self.data

    async def async_apply_entry_options(self, entry) -> None:
        self.config_entry = entry
        self.client.set_battery_profile(entry.options.get(CONF_BATTERY_PROFILE, DEFAULT_BATTERY_PROFILE))
        self._periodic_updates = entry.options.get(CONF_PERIODIC_UPDATES, DEFAULT_PERIODIC_UPDATES)
        self._connected_seconds = entry.options.get(CONF_CONNECTED_SECONDS, DEFAULT_CONNECTED_SECONDS)
        self._disconnected_seconds = entry.options.get(
            CONF_DISCONNECTED_SECONDS, DEFAULT_DISCONNECTED_SECONDS
        )

        if not self._periodic_updates:
            self._planned_disconnect = False
            self._cancel_timers()
            if self.connection_state == CONNECTION_STATE_COOLDOWN:
                self._set_connection_state(CONNECTION_STATE_DISCONNECTED)
                self.async_update_listeners()
            await self.client.set_connection_enabled(True)
            return

        if self.connection_state == CONNECTION_STATE_CONNECTED and self.connected:
            self._schedule_connected_window()
        elif self.connection_state == CONNECTION_STATE_COOLDOWN:
            self._schedule_cooldown()
        self.async_update_listeners()

    async def async_update_runtime_options(self, **updates: Any) -> None:
        new_options = dict(self.config_entry.options)
        new_options.update(updates)
        self.hass.config_entries.async_update_entry(self.config_entry, options=new_options)

    def _cancel_connected_task(self) -> None:
        task = self._connected_task
        self._connected_task = None
        if task is not None:
            task.cancel()

    def _cancel_cooldown_task(self) -> None:
        task = self._cooldown_task
        self._cooldown_task = None
        if task is not None:
            task.cancel()

    def _cancel_timers(self) -> None:
        self._cancel_connected_task()
        self._cancel_cooldown_task()

    def _schedule_connected_window(self) -> None:
        self._cancel_connected_task()
        self._connected_task = self.hass.async_create_background_task(
            self._async_connected_window(),
            f"euc_connected_window_{self.address}",
        )

    async def _async_connected_window(self) -> None:
        try:
            await asyncio.sleep(self._connected_seconds)
            if not self._periodic_updates or not self.connected:
                return
            self._planned_disconnect = True
            await self.client.set_connection_enabled(False)
        except asyncio.CancelledError:
            raise

    def _schedule_cooldown(self) -> None:
        self._cancel_cooldown_task()
        self._cooldown_task = self.hass.async_create_background_task(
            self._async_cooldown_wait(),
            f"euc_cooldown_{self.address}",
        )

    async def _async_cooldown_wait(self) -> None:
        try:
            await asyncio.sleep(self._disconnected_seconds)
            if not self._periodic_updates:
                return
            await self.client.set_connection_enabled(True)
        except asyncio.CancelledError:
            raise

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
