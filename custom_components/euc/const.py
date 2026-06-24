from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "euc"
NAME: Final = "EUC"

CONF_BATTERY_PROFILE: Final = "battery_profile"
DEFAULT_BATTERY_PROFILE: Final = "auto"

VENDOR_LEAPERKIM: Final = "LeaperKim"
VENDOR_BEGODE: Final = "Begode"
VENDOR_UNKNOWN: Final = "Unknown"

PROTOCOL_VETERAN: Final = "veteran"
PROTOCOL_BEGODE: Final = "begode"

MODEL_UNKNOWN: Final = "Unknown"

BLE_SERVICE_UUID: Final = "0000ffe0-0000-1000-8000-00805f9b34fb"
BLE_NOTIFY_UUID: Final = "0000ffe1-0000-1000-8000-00805f9b34fb"
BLE_NOTIFY_SHORT_UUIDS: Final = ("ffe1",)

DEFAULT_BACKOFF_INITIAL: Final = 3
DEFAULT_BACKOFF_MAX: Final = 60
STALE_AFTER: Final = timedelta(seconds=20)

EVENT_EUC_CONNECTED: Final = "euc_connected"
EVENT_EUC_DISCONNECTED: Final = "euc_disconnected"

BATTERY_PROFILES: Final = {
    "auto": {
        "label": "Auto / 67.2 V",
        "scale": 1.0,
        "empty_voltage": 56.0,
        "full_voltage": 67.2,
    },
    "67v": {
        "label": "67.2 V (16s)",
        "scale": 1.0,
        "empty_voltage": 56.0,
        "full_voltage": 67.2,
    },
    "84v": {
        "label": "84.0 V (20s)",
        "scale": 1.25,
        "empty_voltage": 70.0,
        "full_voltage": 84.0,
    },
    "100v": {
        "label": "100.8 V (24s / MSuperX)",
        "scale": 1.5,
        "empty_voltage": 84.0,
        "full_voltage": 100.8,
    },
    "117v": {
        "label": "116.8 V (28s)",
        "scale": 1.7380952380952381,
        "empty_voltage": 98.0,
        "full_voltage": 116.8,
    },
    "134v": {
        "label": "134.4 V (32s)",
        "scale": 2.0,
        "empty_voltage": 112.0,
        "full_voltage": 134.4,
    },
    "151v": {
        "label": "151.2 V (36s)",
        "scale": 2.25,
        "empty_voltage": 126.0,
        "full_voltage": 151.2,
    },
    "168v": {
        "label": "168.0 V (40s)",
        "scale": 2.5,
        "empty_voltage": 140.0,
        "full_voltage": 168.0,
    },
}

VETERAN_ONLY_SENSOR_KEYS: Final = frozenset(
    {
        "pitch_angle",
        "auto_off_seconds",
        "charge_mode",
        "speed_alert",
        "speed_tiltback",
        "firmware_version",
        "pwm",
        "bms1_voltage",
        "bms1_current",
        "bms1_cell_min",
        "bms1_cell_max",
        "bms1_cell_diff",
        "bms1_cell_avg",
        "bms1_cell_count",
        "bms2_voltage",
        "bms2_current",
        "bms2_cell_min",
        "bms2_cell_max",
        "bms2_cell_diff",
        "bms2_cell_avg",
        "bms2_cell_count",
    }
)

BEGODE_ONLY_SENSOR_KEYS: Final = frozenset(
    set()
)

REMOVED_SENSOR_KEYS: Final = frozenset(
    {
        "battery_current",
        "motor_temperature",
    }
)
