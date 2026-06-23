# EUC Home Assistant dev stand

This repository starts with a minimal Home Assistant development stand for the future EUC BLE integration.

## What is included

- `docker-compose.yml` starts a ready Home Assistant container.
- `./data` stores the Home Assistant configuration and runtime state.
- `./custom_components` is mounted into the container as `/config/custom_components`.

That mount is the main development loop: after changing integration code in this repository, restart Home Assistant and it will pick up the updated files.

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

## Planned integration layout

The future integration should live under:

`custom_components/euc/`
