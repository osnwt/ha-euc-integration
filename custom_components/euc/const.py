from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "euc"
NAME: Final = "EUC"

VENDOR_LEAPERKIM: Final = "leaperkim"
MODEL_SHERMAN_L: Final = "Sherman-L"
PROTOCOL_SHERMAN_L: Final = "sherman_l"

BLE_SERVICE_UUID: Final = "0000ffe0-0000-1000-8000-00805f9b34fb"
BLE_NOTIFY_UUID: Final = "0000ffe1-0000-1000-8000-00805f9b34fb"
BLE_NOTIFY_SHORT_UUIDS: Final = ("ffe1",)

DEFAULT_BACKOFF_INITIAL: Final = 3
DEFAULT_BACKOFF_MAX: Final = 60
STALE_AFTER: Final = timedelta(seconds=20)

EVENT_EUC_CONNECTED: Final = "euc_connected"
EVENT_EUC_DISCONNECTED: Final = "euc_disconnected"
