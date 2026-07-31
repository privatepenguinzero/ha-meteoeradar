"""Integrazione custom Meteo e Radar (meteoeradar.it) per Home Assistant."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import MeteoERadarClient, MeteoERadarLocation
from .const import (
    CONF_LANGUAGE,
    CONF_LOCATION,
    CONF_UPDATE_INTERVAL,
    DEFAULT_LANGUAGE,
    DEFAULT_UPDATE_MINUTES,
)
from .coordinator import MeteoERadarCoordinator

PLATFORMS: list[Platform] = [Platform.WEATHER]

type MeteoERadarConfigEntry = ConfigEntry[MeteoERadarCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: MeteoERadarConfigEntry) -> bool:
    """Configura una localita'."""
    location = MeteoERadarLocation.from_dict(entry.data[CONF_LOCATION])
    language = entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)

    client = MeteoERadarClient(async_get_clientsession(hass), language=language)
    interval = timedelta(
        minutes=int(entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_MINUTES))
    )

    coordinator = MeteoERadarCoordinator(hass, entry, client, location, interval)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: MeteoERadarConfigEntry
) -> bool:
    """Rimuove una localita'."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(
    hass: HomeAssistant, entry: MeteoERadarConfigEntry
) -> None:
    """Ricarica l'entry quando cambiano le opzioni."""
    await hass.config_entries.async_reload(entry.entry_id)
