from __future__ import annotations

import binascii
import struct
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from .const import (
    BATTERY_PROFILES,
    DEFAULT_BATTERY_PROFILE,
    MODEL_UNKNOWN,
    PROTOCOL_BEGODE,
    PROTOCOL_VETERAN,
    VENDOR_BEGODE,
    VENDOR_LEAPERKIM,
    VENDOR_UNKNOWN,
)

TelemetrySample = dict[str, Any]

_VETERAN_MODEL_NAMES = {
    0: "Sherman",
    1: "Sherman",
    2: "Abrams",
    3: "Sherman S",
    4: "Patton",
    5: "Lynx",
    6: "Sherman L",
    7: "Patton S",
    8: "Oryx",
    9: "Lynx S",
    42: "Nosfet Apex",
    43: "Nosfet Aero",
    44: "Nosfet Aeon",
}

_PEDALS_MODE_LABELS = {
    0: "Hard",
    1: "Medium",
    2: "Soft",
}


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _u16_be(data: bytes, offset: int) -> int:
    return struct.unpack_from(">H", data, offset)[0]


def _i16_be(data: bytes, offset: int) -> int:
    return struct.unpack_from(">h", data, offset)[0]


def _u32_be(data: bytes, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def _rev_u32_be(data: bytes, offset: int) -> int:
    b0, b1, b2, b3 = struct.unpack_from("4B", data, offset)
    return (b2 << 24) | (b3 << 16) | (b0 << 8) | b1


def _crc32(data: bytes) -> int:
    return binascii.crc32(data) & 0xFFFFFFFF


def _round(value: float, precision: int) -> float:
    return round(value, precision)


def _clamp_percent(value: float) -> int:
    return max(0, min(100, int(round(value))))


def _battery_percent_linear(voltage: float, empty_voltage: float, full_voltage: float) -> int:
    if voltage <= empty_voltage:
        return 0
    if voltage >= full_voltage:
        return 100
    span = full_voltage - empty_voltage
    return _clamp_percent((voltage - empty_voltage) * 100.0 / span)


def _veteran_cells_for_model(model_code: int) -> int:
    if model_code in (4, 7, 43):
        return 30
    if model_code == 8:
        return 42
    if model_code >= 5:
        return 36
    return 24


def _veteran_battery_percent(voltage_centi: int, model_code: int) -> int:
    if model_code < 4:
        return _battery_percent_linear(voltage_centi / 100.0, 79.35, 98.70)
    if model_code in (4, 7, 43):
        return _battery_percent_linear(voltage_centi / 100.0, 99.18, 123.37)
    if model_code in (5, 6, 9, 42, 44):
        return _battery_percent_linear(voltage_centi / 100.0, 119.02, 148.05)
    if model_code == 8:
        return _battery_percent_linear(voltage_centi / 100.0, 138.86, 172.72)
    return 1


def _begode_battery_percent(voltage: float, scale: float) -> int:
    return _battery_percent_linear(voltage, 52.90 * scale, 65.80 * scale)


def _begode_pedals_mode_label(raw_mode: int) -> str | None:
    return _PEDALS_MODE_LABELS.get(2 - raw_mode)


@dataclass
class _VeteranBmsState:
    cell_count: int
    cells: list[float] = field(default_factory=list)
    temps: list[float | None] = field(default_factory=lambda: [None] * 6)
    current: float | None = None

    def __post_init__(self) -> None:
        if not self.cells:
            self.cells = [0.0] * 42

    def summary(self, prefix: str) -> TelemetrySample:
        active_cells = [cell for cell in self.cells[: self.cell_count] if cell > 0]
        sample: TelemetrySample = {}
        if self.current is not None:
            sample[f"{prefix}_current"] = _round(self.current, 2)
        for index, temp in enumerate(self.temps, start=1):
            if temp is not None:
                sample[f"{prefix}_temp_{index}"] = _round(temp, 2)
        if not active_cells:
            return sample
        voltage = sum(active_cells)
        min_cell = min(active_cells)
        max_cell = max(active_cells)
        min_index = active_cells.index(min_cell) + 1
        max_index = active_cells.index(max_cell) + 1
        sample[f"{prefix}_voltage"] = _round(voltage, 3)
        sample[f"{prefix}_cell_min"] = _round(min_cell, 3)
        sample[f"{prefix}_cell_max"] = _round(max_cell, 3)
        sample[f"{prefix}_cell_diff"] = _round(max_cell - min_cell, 3)
        sample[f"{prefix}_cell_avg"] = _round(voltage / len(active_cells), 3)
        sample[f"{prefix}_cell_count"] = len(active_cells)
        sample[f"{prefix}_cell_voltages"] = [_round(cell, 3) for cell in active_cells]
        sample[f"{prefix}_cell_min_v"] = _round(min_cell, 3)
        sample[f"{prefix}_cell_max_v"] = _round(max_cell, 3)
        sample[f"{prefix}_cell_avg_v"] = _round(voltage / len(active_cells), 3)
        sample[f"{prefix}_cell_diff_mv"] = int(round((max_cell - min_cell) * 1000))
        sample[f"{prefix}_cell_min_index"] = min_index
        sample[f"{prefix}_cell_max_index"] = max_index
        return sample


class VeteranParser:
    HEADER = b"\xDC\x5A\x5C"
    MIN_PACKET_LENGTH = 38
    CRC_THRESHOLD = 42

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._latest: TelemetrySample | None = None
        self._bms1 = _VeteranBmsState(cell_count=36)
        self._bms2 = _VeteranBmsState(cell_count=36)

    def feed_data(self, data: bytes) -> list[TelemetrySample]:
        self._buffer.extend(data)
        samples: list[TelemetrySample] = []

        while True:
            header_index = self._buffer.find(self.HEADER)
            if header_index < 0:
                if len(self._buffer) > 2:
                    del self._buffer[:-2]
                break

            if header_index > 0:
                del self._buffer[:header_index]

            if len(self._buffer) < 4:
                break

            packet_length = self._buffer[3]
            if packet_length < self.MIN_PACKET_LENGTH:
                del self._buffer[0]
                continue

            total_length = packet_length + 4
            if len(self._buffer) < total_length:
                break

            frame = bytes(self._buffer[:total_length])
            del self._buffer[:total_length]

            if packet_length > self.CRC_THRESHOLD:
                computed_crc = _crc32(frame[:packet_length])
                received_crc = int.from_bytes(frame[packet_length:packet_length + 4], "big")
                if computed_crc != received_crc:
                    continue

            sample = self._parse_packet(frame)
            if sample is not None:
                self._latest = sample
                samples.append(sample)

        return samples

    def _parse_packet(self, packet: bytes) -> TelemetrySample | None:
        if len(packet) < self.MIN_PACKET_LENGTH + 4:
            return None

        version_raw = _u16_be(packet, 28)
        model_code = version_raw // 1000
        model = _VETERAN_MODEL_NAMES.get(model_code, MODEL_UNKNOWN)

        sample: TelemetrySample = {
            "timestamp": _timestamp(),
            "vendor": VENDOR_LEAPERKIM,
            "model": model,
            "protocol": PROTOCOL_VETERAN,
            "firmware_model_code": model_code,
            "voltage": _round(_u16_be(packet, 4) / 100.0, 2),
            "speed": _round(_i16_be(packet, 6), 1),
            "trip_distance": _round(_rev_u32_be(packet, 8) / 1000.0, 3),
            "total_distance": _round(_rev_u32_be(packet, 12) / 1000.0, 3),
            "phase_current": _round(_i16_be(packet, 16) / 10.0, 1),
            "temperature": _round(_i16_be(packet, 18) / 100.0, 2),
            "auto_off_seconds": _u16_be(packet, 20),
            "charge_mode": _u16_be(packet, 22),
            "speed_alert": _round(_u16_be(packet, 24) / 10.0, 1),
            "speed_tiltback": _round(_u16_be(packet, 26) / 10.0, 1),
            "firmware_version": (
                f"{version_raw // 1000:03d}.{(version_raw % 1000) // 100:01d}.{version_raw % 100:02d}"
            ),
            "pedals_mode": _u16_be(packet, 30),
            "pitch_angle": _round(_i16_be(packet, 32) / 100.0, 2),
            "pwm": _round(_u16_be(packet, 34) / 100.0, 2),
            "battery_level": _veteran_battery_percent(_u16_be(packet, 4), model_code),
        }

        self._update_bms(packet, model_code)
        sample.update(self._bms1.summary("bms1"))
        sample.update(self._bms2.summary("bms2"))
        return sample

    def _update_bms(self, packet: bytes, model_code: int) -> None:
        if len(packet) <= 46 or model_code < 5:
            return

        expected_cells = _veteran_cells_for_model(model_code)
        self._bms1.cell_count = expected_cells
        self._bms2.cell_count = expected_cells

        packet_number = packet[46]
        state = self._bms1 if packet_number < 4 else self._bms2

        if packet_number in (0, 4):
            if len(packet) > 72:
                self._bms1.current = _i16_be(packet, 69) / 100.0
                self._bms2.current = _i16_be(packet, 71) / 100.0
            return

        if packet_number in (1, 5):
            for index in range(15):
                offset = 53 + index * 2
                if offset + 2 > len(packet):
                    break
                state.cells[index] = _i16_be(packet, offset) / 1000.0
            return

        if packet_number in (2, 6):
            for index in range(15):
                offset = 53 + index * 2
                if offset + 2 > len(packet):
                    break
                state.cells[index + 15] = _u16_be(packet, offset) / 1000.0
            return

        if packet_number not in (3, 7):
            return

        for index in range(6):
            offset = 47 + index * 2
            if offset + 2 > len(packet):
                break
            state.temps[index] = _i16_be(packet, offset) / 100.0

        remaining_cells = max(0, expected_cells - 30)
        for index in range(min(12, remaining_cells)):
            offset = 59 + index * 2
            if offset + 2 > len(packet):
                break
            state.cells[index + 30] = _u16_be(packet, offset) / 1000.0

    def snapshot(self) -> TelemetrySample | None:
        return deepcopy(self._latest)


@dataclass(frozen=True)
class BatteryProfile:
    key: str
    scale: float
    empty_voltage: float
    full_voltage: float

    @classmethod
    def from_key(cls, key: str) -> "BatteryProfile":
        profile = BATTERY_PROFILES.get(key, BATTERY_PROFILES[DEFAULT_BATTERY_PROFILE])
        return cls(
            key=key if key in BATTERY_PROFILES else DEFAULT_BATTERY_PROFILE,
            scale=profile["scale"],
            empty_voltage=profile["empty_voltage"],
            full_voltage=profile["full_voltage"],
        )


class BegodeParser:
    HEADER = b"\x55\xAA"
    FOOTER = b"\x5A\x5A\x5A\x5A"
    FRAME_LENGTH = 24

    def __init__(self, battery_profile: str = DEFAULT_BATTERY_PROFILE) -> None:
        self._buffer = bytearray()
        self._latest: TelemetrySample | None = None
        self._state: TelemetrySample = {
            "vendor": VENDOR_BEGODE,
            "model": "MSuperX",
            "protocol": PROTOCOL_BEGODE,
        }
        self._profile = BatteryProfile.from_key(battery_profile)

    def feed_data(self, data: bytes) -> list[TelemetrySample]:
        self._buffer.extend(data)
        samples: list[TelemetrySample] = []

        while True:
            header_index = self._buffer.find(self.HEADER)
            if header_index < 0:
                if len(self._buffer) > 1:
                    del self._buffer[:-1]
                break

            if header_index > 0:
                del self._buffer[:header_index]

            if len(self._buffer) < self.FRAME_LENGTH:
                break

            frame = bytes(self._buffer[: self.FRAME_LENGTH])
            if frame[-4:] != self.FOOTER:
                del self._buffer[0]
                continue

            del self._buffer[: self.FRAME_LENGTH]
            sample = self._parse_frame(frame)
            if sample is not None:
                self._latest = sample
                samples.append(sample)

        return samples

    def _parse_frame(self, frame: bytes) -> TelemetrySample | None:
        frame_type = frame[18]

        if frame_type == 0x00:
            raw_voltage = _u16_be(frame, 2)
            scaled_voltage = raw_voltage * self._profile.scale / 100.0
            self._state.update(
                {
                    "voltage": _round(scaled_voltage, 2),
                    "speed": _round(_i16_be(frame, 4) * 3.6 / 100.0, 1),
                    "trip_distance": _round(_u16_be(frame, 8) / 1000.0, 3),
                    "phase_current": _round(_i16_be(frame, 10) / 100.0, 2),
                    "temperature": _round((_i16_be(frame, 12) / 340.0) + 36.53, 2),
                    "battery_level": _begode_battery_percent(scaled_voltage, self._profile.scale),
                }
            )
        elif frame_type == 0x04:
            settings = _u16_be(frame, 6)
            tiltback_speed = _u16_be(frame, 10)
            raw_pedals_mode = (settings >> 13) & 0x03
            self._state.update(
                {
                    "total_distance": _round(_u32_be(frame, 2) / 1000.0, 3),
                    "pedals_mode": _begode_pedals_mode_label(raw_pedals_mode),
                    "speed_tiltback": 0 if tiltback_speed >= 100 else float(tiltback_speed),
                }
            )
        elif frame_type == 0x07:
            self._state.update(
                {
                    "battery_current": _round((-1.0) * _i16_be(frame, 2) / 100.0, 2),
                    "motor_temperature": _round(_i16_be(frame, 6) / 100.0, 2),
                }
            )
        else:
            return None

        sample = deepcopy(self._state)
        sample["timestamp"] = _timestamp()
        return sample

    def snapshot(self) -> TelemetrySample | None:
        return deepcopy(self._latest)

    def set_battery_profile(self, battery_profile: str) -> None:
        self._profile = BatteryProfile.from_key(battery_profile)


class MultiProtocolParser:
    def __init__(self, battery_profile: str = DEFAULT_BATTERY_PROFILE) -> None:
        self._parsers = {
            PROTOCOL_VETERAN: VeteranParser(),
            PROTOCOL_BEGODE: BegodeParser(battery_profile=battery_profile),
        }
        self._selected_protocol: str | None = None
        self._latest: TelemetrySample | None = None

    def feed_data(self, data: bytes) -> list[TelemetrySample]:
        if self._selected_protocol is not None:
            samples = self._parsers[self._selected_protocol].feed_data(data)
            if samples:
                self._latest = samples[-1]
            return samples

        all_samples: list[TelemetrySample] = []
        for protocol, parser in self._parsers.items():
            samples = parser.feed_data(data)
            if not samples:
                continue
            if self._selected_protocol is None:
                self._selected_protocol = protocol
            all_samples.extend(samples)

        if all_samples:
            self._latest = all_samples[-1]
        return all_samples

    def snapshot(self) -> TelemetrySample | None:
        return deepcopy(self._latest)

    def set_battery_profile(self, battery_profile: str) -> None:
        begode_parser = self._parsers.get(PROTOCOL_BEGODE)
        if begode_parser is not None:
            begode_parser.set_battery_profile(battery_profile)


ShermanLParser = VeteranParser
