"""Config flow per Meteo e Radar."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import (
    MeteoERadarClient,
    MeteoERadarConnectionError,
    MeteoERadarLocation,
    MeteoERadarNoResultsError,
)
from .const import (
    CONF_LANGUAGE,
    CONF_LOCATION,
    CONF_QUERY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_LANGUAGE,
    DEFAULT_UPDATE_MINUTES,
    DOMAIN,
    MAX_UPDATE_MINUTES,
    MIN_UPDATE_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema({vol.Optional(CONF_QUERY, default=""): str})


class MeteoERadarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Guida l'utente nella scelta della localita'."""

    VERSION = 1

    def __init__(self) -> None:
        self._candidates: list[MeteoERadarLocation] = []

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> MeteoERadarOptionsFlow:
        return MeteoERadarOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Primo passo: nome della localita' oppure coordinate di Home Assistant."""
        errors: dict[str, str] = {}

        if user_input is not None:
            query = (user_input.get(CONF_QUERY) or "").strip()
            client = MeteoERadarClient(async_get_clientsession(self.hass))

            try:
                if query:
                    self._candidates = await client.async_search(query)
                else:
                    self._candidates = [
                        await client.async_reverse(
                            self.hass.config.latitude,
                            self.hass.config.longitude,
                            self.hass.config.elevation,
                        )
                    ]
            except MeteoERadarNoResultsError:
                errors["base"] = "no_results"
            except MeteoERadarConnectionError as err:
                _LOGGER.debug("Errore di connessione durante la ricerca: %s", err)
                errors["base"] = "cannot_connect"
            else:
                if len(self._candidates) == 1:
                    return await self._async_create(self._candidates[0])
                return await self.async_step_location()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors
        )

    async def async_step_location(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Disambigua tra piu' risultati della ricerca."""
        if user_input is not None:
            selected = next(
                (
                    candidate
                    for candidate in self._candidates
                    if candidate.geo_object_key == user_input[CONF_LOCATION]
                ),
                None,
            )
            if selected is not None:
                return await self._async_create(selected)

        options = [
            {"value": candidate.geo_object_key, "label": candidate.name}
            for candidate in self._candidates
        ]
        schema = vol.Schema(
            {
                vol.Required(CONF_LOCATION): SelectSelector(
                    SelectSelectorConfig(options=options, mode=SelectSelectorMode.LIST)
                )
            }
        )
        return self.async_show_form(step_id="location", data_schema=schema)

    async def _async_create(self, location: MeteoERadarLocation) -> ConfigFlowResult:
        """Crea la config entry, evitando duplicati sulla stessa localita'."""
        await self.async_set_unique_id(f"{DOMAIN}-{location.geo_object_key}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=location.name,
            data={
                CONF_LOCATION: location.as_dict(),
                CONF_LANGUAGE: DEFAULT_LANGUAGE,
            },
            options={CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_MINUTES},
        )


class MeteoERadarOptionsFlow(OptionsFlow):
    """Permette di regolare la frequenza di aggiornamento."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_UPDATE_INTERVAL: int(user_input[CONF_UPDATE_INTERVAL])}
            )

        current = self.config_entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_MINUTES
        )
        schema = vol.Schema(
            {
                vol.Required(CONF_UPDATE_INTERVAL, default=current): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_UPDATE_MINUTES,
                        max=MAX_UPDATE_MINUTES,
                        step=1,
                        mode=NumberSelectorMode.BOX,
                        unit_of_measurement="min",
                    )
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
