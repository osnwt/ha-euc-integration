from __future__ import annotations

import binascii
import struct
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

TelemetrySample = dict[str, Any]


class ShermanLParser:
    """Parse Sherman-L notifications from BLE serial."""

    HEADER = b"\xDC\x5A\x5C"
    MIN_PACKET_LENGTH = 38
    CRC_THRESHOLD = 42

    def __init__(self) -> None:
        self._buffer = bytearray()
        self._latest: TelemetrySample | None = None

    @staticmethod
    def _u16_be(data: bytes, offset: int) -> int:
        return struct.unpack_from(">H", data, offset)[0]

    @staticmethod
    def _i16_be(data: bytes, offset: int) -> int:
        return struct.unpack_from(">h", data, offset)[0]

    @staticmethod
    def _rev_u32_be(data: bytes, offset: int) -> int:
        b0, b1, b2, b3 = struct.unpack_from("4B", data, offset)
        return (b2 << 24) | (b3 << 16) | (b0 << 8) | b1

    @staticmethod
    def _crc32(data: bytes) -> int:
        return binascii.crc32(data) & 0xFFFFFFFF

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
                computed_crc = self._crc32(frame[:packet_length])
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

        version_raw = self._u16_be(packet, 28)

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "voltage": round(self._u16_be(packet, 4) / 100.0, 2),
            "speed": round(self._i16_be(packet, 6), 1),
            "trip_distance": round(self._rev_u32_be(packet, 8) / 1000.0, 3),
            "total_distance": round(self._rev_u32_be(packet, 12) / 1000.0, 3),
            "phase_current": round(self._i16_be(packet, 16), 1),
            "temperature": round(self._i16_be(packet, 18) / 100.0, 2),
            "auto_off_seconds": self._u16_be(packet, 20),
            "charge_mode": self._u16_be(packet, 22),
            "speed_alert": round(self._u16_be(packet, 24) / 10.0, 1),
            "speed_tiltback": round(self._u16_be(packet, 26) / 10.0, 1),
            "firmware_version": f"{version_raw // 1000:03d}.{(version_raw % 1000) // 100:01d}.{version_raw % 100:02d}",
            "pedals_mode": self._u16_be(packet, 30),
            "pitch_angle": round(self._i16_be(packet, 32) / 100.0, 2),
            "pwm": self._u16_be(packet, 34),
            "protocol": "sherman_l",
        }

    def snapshot(self) -> TelemetrySample | None:
        return deepcopy(self._latest)
