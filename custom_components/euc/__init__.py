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
