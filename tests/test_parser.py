from custom_components.euc.parser import ShermanLParser


def _build_packet() -> bytes:
    payload = bytearray(38)
    payload[0:4] = bytes((0xDC, 0x5A, 0x5C, 0x26))
    payload[4:6] = (13420).to_bytes(2, "big", signed=False)
    payload[6:8] = (37).to_bytes(2, "big", signed=True)
    payload[8:12] = bytes((0x00, 0x64, 0x00, 0x00))
    payload[12:16] = bytes((0x00, 0xC8, 0x00, 0x00))
    payload[16:18] = (15).to_bytes(2, "big", signed=True)
    payload[18:20] = (2534).to_bytes(2, "big", signed=True)
    payload[20:22] = (300).to_bytes(2, "big", signed=False)
    payload[22:24] = (1).to_bytes(2, "big", signed=False)
    payload[24:26] = (4500).to_bytes(2, "big", signed=False)
    payload[26:28] = (5000).to_bytes(2, "big", signed=False)
    payload[28:30] = (1234).to_bytes(2, "big", signed=False)
    payload[30:32] = (2).to_bytes(2, "big", signed=False)
    payload[32:34] = (-125).to_bytes(2, "big", signed=True)
    payload[34:36] = (67).to_bytes(2, "big", signed=False)
    return bytes(payload) + b"\x00\x00\x00\x00"


def test_sherman_l_parser_extracts_expected_fields() -> None:
    parser = ShermanLParser()

    samples = parser.feed_data(_build_packet())

    assert len(samples) == 1
    sample = samples[0]
    assert sample["voltage"] == 134.2
    assert sample["speed"] == 37.0
    assert sample["trip_distance"] == 0.1
    assert sample["total_distance"] == 0.2
    assert sample["phase_current"] == 15.0
    assert sample["temperature"] == 25.34
    assert sample["speed_alert"] == 450.0
    assert sample["speed_tiltback"] == 500.0
    assert sample["firmware_version"] == "001.2.34"
    assert sample["pitch_angle"] == -1.25
    assert sample["pwm"] == 67
