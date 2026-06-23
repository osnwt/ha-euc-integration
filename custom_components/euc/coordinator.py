from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .ble import EUCBleClient
from .const import (
    DOMAIN,
    EVENT_EUC_CONNECTED,
    EVENT_EUC_DISCONNECTED,
    MODEL_SHERMAN_L,
    NAME,
    PROTOCOL_SHERMAN_L,
    STALE_AFTER,
    VENDOR_LEAPERKIM,
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
        self.client = EUCBleClient(
            hass=hass,
            address=self.address,
            on_sample=self._handle_sample,
            on_availability_changed=self._handle_availability_changed,
        )
        self.data = None
        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, self.address)},
            connections={(CONNECTION_BLUETOOTH, self.address)},
            name=entry.title or NAME,
            manufacturer="LeaperKim",
            model=MODEL_SHERMAN_L,
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
            "vendor": VENDOR_LEAPERKIM,
            "model": MODEL_SHERMAN_L,
            "protocol": PROTOCOL_SHERMAN_L,
        }
        if self.last_seen is not None:
            payload["last_seen"] = self.last_seen.isoformat()
        if self.data is not None:
            payload["sample"] = dict(self.data)
        return payload

    def _handle_sample(self, sample: TelemetrySample) -> None:
        self.connected = True
        self.last_seen = datetime.now(UTC)
        self.async_set_updated_data(sample)

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
