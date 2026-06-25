# EUC Home Assistant integration

This repository contains a custom Home Assistant integration for `EUC` (electric unicycles) over Bluetooth Low Energy, plus a local Home Assistant development stand for testing it.

The integration is focused on live EUC telemetry in Home Assistant: voltage, battery, speed, distance, temperatures, current, ride state, and model-specific attributes exposed by supported protocols.

## Current support

Supported EUC brand families at the moment:

- `LeaperKim / Veteran`
- `Begode / Gotway`

Currently covered or explicitly mapped models include:

- `LeaperKim / Veteran`: `Sherman`, `Abrams`, `Sherman S`, `Patton`, `Lynx`, `Sherman L`, `Patton S`, `Oryx`, `Lynx S`, `Nosfet Apex`, `Nosfet Aero`, `Nosfet Aeon`
- `Begode / Gotway`: current parser coverage is for the Begode/Gotway protocol family; test coverage currently includes `MSuperX`

Current parser tests explicitly verify:

- `LeaperKim / Veteran`: `Sherman L`
- `Begode / Gotway`: `MSuperX`

Discovery is currently configured for Bluetooth devices advertising as:

- `LeaperKim*`
- `Veteran*`
- `Begode*`
- `Gotway*`

At the current stage, discovery is still limited and manual setup by BLE MAC address may be required in the config flow.

## Project layout

- `docker-compose.yml` starts a ready Home Assistant container.
- `./data` stores the Home Assistant configuration and runtime state.
- `./custom_components` is mounted into the container as `/config/custom_components`.
- `./custom_components/euc` contains the integration code.
- `./assets` stores repository-level branding assets for GitHub/HACS publishing.

That mount is the main development loop: after changing integration code in this repository, restart Home Assistant and it will pick up the updated files.

## Current state

- Bluetooth config flow is enabled.
- Multi-protocol parsing is implemented for the currently supported EUC families.
- Repository and bundled brand assets are included for Home Assistant and HACS packaging.
- The repository includes a local Docker-based Home Assistant stand for development and validation.

## Requirements

- Home Assistant with the built-in `Bluetooth` integration enabled
- A connectable Bluetooth path to the wheel
- For the intended deployment model: one or more ESPHome BLE Proxy nodes

Important behavior:

- The integration does not perform its own BLE scan outside Home Assistant.
- The wheel must first be discovered by the Home Assistant Bluetooth stack.
- In BLE Proxy setups this means the proxy must see the wheel advertisement before the integration can connect.

## Installation

### Install with HACS

1. Open `HACS -> Integrations`.
2. Open the top-right menu and choose `Custom repositories`.
3. Add this repository URL:

```text
https://github.com/osnwt/ha-euc-integration
```

4. Select repository type `Integration`.
5. Find `EUC` in HACS and install it.
6. Restart Home Assistant.
7. Make sure the built-in `Bluetooth` integration is enabled.
8. Make sure your wheel is visible through Home Assistant Bluetooth or ESPHome BLE Proxy.
9. Add `EUC` from `Settings -> Devices & Services`.

### Manual Installation

1. Copy `custom_components/euc` into your Home Assistant `config/custom_components/` directory.
2. Restart Home Assistant.
3. Make sure the built-in `Bluetooth` integration is enabled.
4. Make sure your wheel is visible through Home Assistant Bluetooth or ESPHome BLE Proxy.
5. Add `EUC` from `Settings -> Devices & Services`.

## Start

```bash
docker compose up -d
```

Or:

```bash
./scripts/start.sh
```

Open Home Assistant at `http://localhost:8123`.

The Docker project and container use generic names so this stand can be copied into another integration repository without renaming compose resources.

## Development loop

```bash
docker compose restart homeassistant
docker compose logs -f homeassistant
```

Or use helper scripts:

```bash
./scripts/restart.sh
./scripts/logs.sh
./scripts/status.sh
./scripts/stop.sh
```

`restart.sh` and `stop.sh` use an extended shutdown timeout so Home Assistant has time to close SQLite cleanly before the container is stopped.

## Data and backups

All Home Assistant state is stored in `./data`.

Quick backup:

```bash
tar -czf ha-data-backup.tgz data
```

Quick restore:

```bash
tar -xzf ha-data-backup.tgz
```

## BLE proxy note

This stand is intended to work with ESPHome BLE Proxy instead of a host BLE adapter.

At this stage no special YAML configuration is required in Home Assistant. After first boot:

1. Finish initial Home Assistant onboarding.
2. Add the ESPHome device or use the discovered proxy.
3. Confirm that the proxy appears in Home Assistant Bluetooth integrations.

## Project layout

```text
custom_components/euc/
  __init__.py
  manifest.json
  config_flow.py
  ble.py
  parser.py
  coordinator.py
  sensor.py
  binary_sensor.py
  number.py
  switch.py
  brand/
  translations/

tests/
  test_parser.py
```

## Example dashboards

The `examples/` directory contains Lovelace examples for supported wheels and layouts, including:

- `examples/sherman_l.yaml`
- `examples/msuperx.yaml`
- `examples/panel_tabs.yaml`

These examples use custom Lovelace cards:

- `custom:decluttering-card`
- `custom:apexcharts-card` for Smart BMS cell-voltage charts

They are intended as examples and require the corresponding frontend cards to be installed in Home Assistant.

## Branding and HACS

- `assets/icon.png` and `assets/logo.png` are the repository branding assets.
- `custom_components/euc/brand/icon.png` and `custom_components/euc/brand/logo.png` are bundled with the installed integration.
- `hacs.json` is included so the repository is ready for HACS custom-repository publication from `https://github.com/osnwt/ha-euc-integration`.

Note: local `brand/` assets help installed integration branding in Home Assistant. HACS repository-card branding is handled separately by HACS/GitHub metadata, so the future GitHub repository and release setup still matters.
