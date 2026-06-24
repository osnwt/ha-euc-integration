from __future__ import annotations

import logging
from time import perf_counter

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


async def async_setup(hass, config: dict) -> bool:
    return True


async def async_setup_entry(hass, entry) -> bool:
    from .const import DOMAIN
    from .coordinator import EUCCoordinator

    started_at = perf_counter()
    _LOGGER.info("EUC setup_entry start: entry_id=%s title=%s", entry.entry_id, entry.title)

    coordinator = EUCCoordinator(hass, entry)
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # One-shot migration already executed once to realign existing wheels with the
    # current SmartBMS defaults. Keep the helper below for reference, but do not
    # run it automatically anymore to avoid overriding user entity preferences.
    # await _async_sync_bms_entity_defaults(hass, entry)
    _LOGGER.info(
        "EUC setup_entry platforms ready: entry_id=%s elapsed=%.3fs",
        entry.entry_id,
        perf_counter() - started_at,
    )
    await coordinator.async_start()
    _LOGGER.info(
        "EUC setup_entry done: entry_id=%s elapsed=%.3fs",
        entry.entry_id,
        perf_counter() - started_at,
    )

    return True


async def async_unload_entry(hass, entry) -> bool:
    from .const import DOMAIN

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_stop()
    return unload_ok


async def _async_reload_entry(hass, entry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


# One-shot BMS entity migration, kept only as a commented reference.
#
# from homeassistant.helpers import entity_registry as er
# _ENTRY_DATA_BMS_DEFAULTS_SYNCED = "_bms_defaults_synced"
# _BMS_ENABLED_KEYS = frozenset({"bms1_cells", "bms2_cells"})
# _BMS_DISABLED_KEYS = frozenset(
#     {
#         "bms1_voltage",
#         "bms1_current",
#         "bms1_cell_min",
#         "bms1_cell_max",
#         "bms1_cell_diff",
#         "bms1_cell_avg",
#         "bms1_cell_count",
#         "bms2_voltage",
#         "bms2_current",
#         "bms2_cell_min",
#         "bms2_cell_max",
#         "bms2_cell_diff",
#         "bms2_cell_avg",
#         "bms2_cell_count",
#     }
# )
#
# async def _async_sync_bms_entity_defaults(hass, entry) -> None:
#     if entry.data.get(_ENTRY_DATA_BMS_DEFAULTS_SYNCED):
#         return
#
#     registry = er.async_get(hass)
#     entries = er.async_entries_for_config_entry(registry, entry.entry_id)
#     updated = 0
#
#     for entity_entry in entries:
#         unique_id = entity_entry.unique_id
#         if not unique_id.startswith(f"{entry.unique_id or entry.data['address']}_"):
#             continue
#
#         sensor_key = unique_id.split("_", 1)[1]
#         if sensor_key in _BMS_ENABLED_KEYS:
#             if entity_entry.disabled_by is not None:
#                 registry.async_update_entity(entity_entry.entity_id, disabled_by=None)
#                 updated += 1
#             continue
#
#         if sensor_key in _BMS_DISABLED_KEYS and entity_entry.disabled_by is None:
#             registry.async_update_entity(
#                 entity_entry.entity_id,
#                 disabled_by=er.RegistryEntryDisabler.INTEGRATION,
#             )
#             updated += 1
#
#     hass.config_entries.async_update_entry(
#         entry,
#         data={**entry.data, _ENTRY_DATA_BMS_DEFAULTS_SYNCED: True},
#     )
#     _LOGGER.info(
#         "EUC BMS entity defaults synced: entry_id=%s updated=%s",
#         entry.entry_id,
#         updated,
#     )
