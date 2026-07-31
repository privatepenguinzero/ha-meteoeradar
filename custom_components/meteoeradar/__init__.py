"""Integrazione custom Meteo e Radar (meteoeradar.it) per Home Assistant."""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    MeteoERadarClient,
    MeteoERadarError,
    MeteoERadarLocation,
    resolve_locale,
)
from .const import (
    CONF_LANGUAGE,
    CONF_LOCATION,
    CONF_UPDATE_INTERVAL,
    DEFAULT_LANGUAGE,
    DEFAULT_UPDATE_MINUTES,
)
from .coordinator import MeteoERadarCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.WEATHER, Platform.SENSOR]

type MeteoERadarConfigEntry = ConfigEntry[MeteoERadarCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: MeteoERadarConfigEntry) -> bool:
    """Configura una localita'."""
    location = MeteoERadarLocation.from_dict(entry.data[CONF_LOCATION])

    # L'opzione ha la precedenza sul valore salvato alla creazione dell'entry.
    configured = entry.options.get(
        CONF_LANGUAGE, entry.data.get(CONF_LANGUAGE, DEFAULT_LANGUAGE)
    )
    language, region = resolve_locale(
        configured, hass.config.language, hass.config.country
    )

    client = MeteoERadarClient(
        async_get_clientsession(hass), language=language, region=region
    )
    location = await _async_ensure_country_code(hass, entry, client, location)
    interval = timedelta(
        minutes=int(entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_MINUTES))
    )

    coordinator = MeteoERadarCoordinator(hass, entry, client, location, interval)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def _async_ensure_country_code(
    hass: HomeAssistant,
    entry: MeteoERadarConfigEntry,
    client: MeteoERadarClient,
    location: MeteoERadarLocation,
) -> MeteoERadarLocation:
    """Recupera il codice paese per le entry create prima della 1.1.0.

    Serve ai pollini, che senza ``isoCountryCode`` ricevono un 400. Se la
    risoluzione fallisce si prosegue lo stesso: a mancare saranno solo i
    sensori dei pollini.
    """
    if location.iso_country_code:
        return location

    try:
        resolved = await client.async_by_key(location.geo_object_key)
    except MeteoERadarError as err:
        _LOGGER.debug(
            "Codice paese non risolvibile per %s, i pollini resteranno assenti: %s",
            location.name,
            err,
        )
        return location

    updated = replace(location, iso_country_code=resolved.iso_country_code)
    hass.config_entries.async_update_entry(
        entry,
        data={**entry.data, CONF_LOCATION: updated.as_dict()},
    )
    return updated


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
