from custom_components.euc.parser import BegodeParser, MultiProtocolParser, VeteranParser


def _build_veteran_packet(*, version: int = 6234) -> bytes:
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
    payload[28:30] = version.to_bytes(2, "big", signed=False)
    payload[30:32] = (2).to_bytes(2, "big", signed=False)
    payload[32:34] = (-125).to_bytes(2, "big", signed=True)
    payload[34:36] = (67).to_bytes(2, "big", signed=False)
    return bytes(payload) + b"\x00\x00\x00\x00"


def _build_begode_frame_a() -> bytes:
    return bytes.fromhex("55AA19C1000000000000008CF0000001FFF800185A5A5A5A")


def _build_begode_frame_b() -> bytes:
    return bytes.fromhex("55AA000060D248001C20006400010007000804185A5A5A5A")


def test_veteran_parser_extracts_expected_fields() -> None:
    parser = VeteranParser()

    samples = parser.feed_data(_build_veteran_packet())

    assert len(samples) == 1
    sample = samples[0]
    assert sample["vendor"] == "LeaperKim"
    assert sample["model"] == "Sherman L"
    assert sample["protocol"] == "veteran"
    assert sample["battery_level"] == 52
    assert sample["voltage"] == 134.2
    assert sample["speed"] == 37.0
    assert sample["trip_distance"] == 0.1
    assert sample["total_distance"] == 0.2
    assert sample["phase_current"] == 15.0
    assert sample["temperature"] == 25.34
    assert sample["speed_alert"] == 450.0
    assert sample["speed_tiltback"] == 500.0
    assert sample["firmware_version"] == "006.2.34"
    assert sample["pitch_angle"] == -1.25
    assert sample["pwm"] == 67


def test_veteran_parser_maps_lynx_s_model() -> None:
    parser = VeteranParser()

    samples = parser.feed_data(_build_veteran_packet(version=9210))

    assert len(samples) == 1
    assert samples[0]["model"] == "Lynx S"
    assert samples[0]["firmware_version"] == "009.2.10"


def test_begode_parser_extracts_live_and_total_data() -> None:
    parser = BegodeParser(battery_profile="67v")

    samples_a = parser.feed_data(_build_begode_frame_a())
    samples_b = parser.feed_data(_build_begode_frame_b())

    assert len(samples_a) == 1
    assert len(samples_b) == 1
    sample = samples_b[0]
    assert sample["vendor"] == "Begode"
    assert sample["model"] == "MSuperX"
    assert sample["protocol"] == "begode"
    assert sample["voltage"] == 65.93
    assert sample["speed"] == 0.0
    assert sample["phase_current"] == 1.4
    assert sample["temperature"] == 24.48
    assert sample["battery_level"] == 89
    assert sample["total_distance"] == 24.786
    assert sample["speed_tiltback"] == 0
    assert sample["pedals_mode"] == 0


def test_multi_protocol_parser_auto_detects_family() -> None:
    parser = MultiProtocolParser(battery_profile="100v")

    veteran_samples = parser.feed_data(_build_veteran_packet())
    begode_samples = parser.feed_data(_build_begode_frame_a())

    assert len(veteran_samples) == 1
    assert veteran_samples[0]["protocol"] == "veteran"
    assert begode_samples == []


def test_begode_parser_applies_configured_battery_profile() -> None:
    parser = BegodeParser(battery_profile="100v")

    samples = parser.feed_data(_build_begode_frame_a())

    assert len(samples) == 1
    assert samples[0]["voltage"] == 98.89
