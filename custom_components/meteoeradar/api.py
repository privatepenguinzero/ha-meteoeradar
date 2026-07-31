"""Client asincrono per le API pubbliche usate da meteoeradar.it."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

import aiohttp
from yarl import URL

from .const import (
    APP_API_BASE,
    APP_API_TOKEN,
    APP_API_VERSION,
    APP_APPLICATION,
    DEFAULT_HEADERS,
    FALLBACK_LANGUAGE,
    LANGUAGE_AUTO,
    LANGUAGE_REGIONS,
    LOC_ALTITUDE,
    LOC_ASTRO_LATITUDE,
    LOC_ASTRO_LONGITUDE,
    LOC_GRID_LATITUDE,
    LOC_GRID_LONGITUDE,
    LOC_ISO_COUNTRY,
    LOC_KEY,
    LOC_LATITUDE,
    LOC_LOCATION_ID,
    LOC_LONGITUDE,
    LOC_NAME,
    LOC_TIMEZONE,
    PATH_AQI,
    PATH_ASTRO,
    PATH_FORECAST,
    PATH_GEOCODING,
    PATH_GEOKEYCODING,
    PATH_POLLEN,
    PATH_REVERSE_GEOCODING,
    PATH_SHORTCAST,
    POLLEN_LANGUAGE,
    REQUEST_TIMEOUT,
    WEB_API_BASE,
    WEB_API_TOKEN,
)

_LOGGER = logging.getLogger(__name__)


class MeteoERadarError(Exception):
    """Errore generico del client."""


class MeteoERadarConnectionError(MeteoERadarError):
    """Il backend non e' raggiungibile o ha risposto con un errore HTTP."""


class MeteoERadarNoResultsError(MeteoERadarError):
    """La ricerca geografica non ha prodotto risultati."""


@dataclass(frozen=True, slots=True)
class MeteoERadarLocation:
    """Localita' risolta, con tutte le chiavi necessarie alle chiamate meteo."""

    geo_object_key: str
    name: str
    latitude: float
    longitude: float
    timezone: str
    location_id: str
    altitude: int | None = None
    grid_latitude: str | None = None
    grid_longitude: str | None = None
    astro_latitude: str | None = None
    astro_longitude: str | None = None
    iso_country_code: str | None = None

    def as_dict(self) -> dict[str, Any]:
        """Serializza per il salvataggio nella config entry."""
        return {
            LOC_KEY: self.geo_object_key,
            LOC_NAME: self.name,
            LOC_LATITUDE: self.latitude,
            LOC_LONGITUDE: self.longitude,
            LOC_ALTITUDE: self.altitude,
            LOC_TIMEZONE: self.timezone,
            LOC_LOCATION_ID: self.location_id,
            LOC_GRID_LATITUDE: self.grid_latitude,
            LOC_GRID_LONGITUDE: self.grid_longitude,
            LOC_ASTRO_LATITUDE: self.astro_latitude,
            LOC_ASTRO_LONGITUDE: self.astro_longitude,
            LOC_ISO_COUNTRY: self.iso_country_code,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MeteoERadarLocation:
        """Ricostruisce la localita' dai dati della config entry."""
        return cls(
            geo_object_key=data[LOC_KEY],
            name=data[LOC_NAME],
            latitude=data[LOC_LATITUDE],
            longitude=data[LOC_LONGITUDE],
            altitude=data.get(LOC_ALTITUDE),
            timezone=data[LOC_TIMEZONE],
            location_id=data[LOC_LOCATION_ID],
            grid_latitude=data.get(LOC_GRID_LATITUDE),
            grid_longitude=data.get(LOC_GRID_LONGITUDE),
            astro_latitude=data.get(LOC_ASTRO_LATITUDE),
            astro_longitude=data.get(LOC_ASTRO_LONGITUDE),
            iso_country_code=data.get(LOC_ISO_COUNTRY),
        )

    @classmethod
    def from_placemark(cls, payload: dict[str, Any]) -> MeteoERadarLocation:
        """Costruisce la localita' da un elemento delle API di ricerca."""
        geo = payload.get("geoObject") or {}
        keys = payload.get("contentKeys") or {}

        forecast_key = keys.get("forecastKey") or {}
        location_id = forecast_key.get("location_id")
        if not location_id:
            raise MeteoERadarNoResultsError(
                "La localita' restituita non espone un forecastKey utilizzabile"
            )

        grid = (keys.get("nowcastKey") or {}).get("woGridKey") or {}
        astro = (keys.get("astroKey") or {}).get("woGridKey") or {}

        return cls(
            geo_object_key=str(geo.get("geoObjectKey") or location_id),
            name=_display_name(payload),
            latitude=float(geo["latitude"]),
            longitude=float(geo["longitude"]),
            altitude=geo.get("altitude"),
            timezone=geo.get("timeZone") or "UTC",
            location_id=str(location_id),
            grid_latitude=grid.get("gridLatitude"),
            grid_longitude=grid.get("gridLongitude"),
            astro_latitude=astro.get("gridLatitude"),
            astro_longitude=astro.get("gridLongitude"),
            iso_country_code=geo.get("iso-3166-1"),
        )


def _display_name(payload: dict[str, Any]) -> str:
    """Nome leggibile, es. "Roma (Lazio, Italia)"."""
    geo = payload.get("geoObject") or {}
    display = geo.get("displayName") or {}
    primary = display.get("primaryName") or geo.get("locationName") or "?"
    secondary = [str(name) for name in (display.get("secondaryNames") or []) if name]
    if secondary:
        return f"{primary} ({', '.join(secondary)})"
    return str(primary)


def resolve_locale(
    configured: str | None,
    hass_language: str | None,
    hass_country: str | None,
) -> tuple[str, str]:
    """Determina lingua e regione da usare con le API.

    ``configured`` e' la scelta dell'utente (``auto``/``it``/``en``); con
    ``auto`` si segue la lingua di Home Assistant, qualunque essa sia — il
    backend ripiega sull'inglese per i codici che non conosce.

    La regione viene dal paese configurato in Home Assistant perche' orienta la
    ricerca geografica: cercare "Milano" con ``region=GB`` restituisce una
    localita' in Texas.
    """
    language = (configured or LANGUAGE_AUTO).strip().lower()
    if language in ("", LANGUAGE_AUTO):
        language = (hass_language or FALLBACK_LANGUAGE).split("-")[0].lower()
    if not language:
        language = FALLBACK_LANGUAGE

    region = hass_country or LANGUAGE_REGIONS.get(language) or language.upper()
    return language, region.upper()


def _round_to(value: float, step: float) -> str:
    """Arrotonda al multiplo di ``step``, come fa il frontend del sito."""
    rounded = round(value / step) * step
    return str(round(rounded, 3))


class MeteoERadarClient:
    """Wrapper minimale sui due backend usati dal sito."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        language: str = "it",
        region: str = "IT",
    ) -> None:
        self._session = session
        self._language = language
        self._region = region

    # -- HTTP ------------------------------------------------------------------

    async def _get(
        self, base: str, path: str, params: dict[str, Any], token: str
    ) -> Any:
        """Esegue una GET.

        Il token va concatenato grezzo: il backend rifiuta con 401 se i ``=``
        finali arrivano percent-encoded, quindi l'URL viene costruito a mano e
        passato a yarl come gia' codificato.
        """
        query = urlencode(
            {key: value for key, value in params.items() if value not in (None, "")}
        )
        url = URL(f"{base}/{path}?{query}&c={token}", encoded=True)

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                response = await self._session.get(url, headers=DEFAULT_HEADERS)
                # La ricerca geografica risponde 204 quando non trova nulla.
                if response.status == 204:
                    return None
                if response.status != 200:
                    body = (await response.text())[:200]
                    raise MeteoERadarConnectionError(
                        f"HTTP {response.status} da {path}: {body}"
                    )
                return await response.json(content_type=None)
        except TimeoutError as err:
            raise MeteoERadarConnectionError(f"Timeout su {path}") from err
        except aiohttp.ClientError as err:
            raise MeteoERadarConnectionError(f"Errore di rete su {path}: {err}") from err

    async def _get_app(self, path: str, params: dict[str, Any]) -> Any:
        return await self._get(
            APP_API_BASE,
            path,
            {
                "language": self._language,
                "region": self._region,
                "application": APP_APPLICATION,
                "mv": "10",
                "av": APP_API_VERSION,
                **params,
            },
            APP_API_TOKEN,
        )

    async def _get_web(self, path: str, params: dict[str, Any]) -> Any:
        return await self._get(WEB_API_BASE, path, params, WEB_API_TOKEN)

    # -- Ricerca geografica ----------------------------------------------------

    async def async_search(self, name: str) -> list[MeteoERadarLocation]:
        """Cerca localita' per nome."""
        payload = await self._get_app(PATH_GEOCODING, {"name": name})
        if not isinstance(payload, list) or not payload:
            raise MeteoERadarNoResultsError(f"Nessun risultato per '{name}'")
        return [MeteoERadarLocation.from_placemark(item) for item in payload]

    async def async_reverse(
        self, latitude: float, longitude: float, altitude: float | None = None
    ) -> MeteoERadarLocation:
        """Risolve la localita' piu' vicina a delle coordinate.

        Il sito arrotonda le coordinate prima di interrogare il backend
        (0.02 gradi in latitudine, 0.016 in longitudine); qui si fa lo stesso
        per massimizzare i cache hit lato server.
        """
        params: dict[str, Any] = {
            "latitude": _round_to(latitude, 0.02),
            "longitude": _round_to(longitude, 0.016),
        }
        if altitude is not None:
            params["altitude"] = str(int(round(altitude / 50.0)) * 50)

        payload = await self._get_app(PATH_REVERSE_GEOCODING, params)
        if not isinstance(payload, list) or not payload:
            raise MeteoERadarNoResultsError(
                f"Nessuna localita' per {latitude}, {longitude}"
            )
        return MeteoERadarLocation.from_placemark(payload[0])

    async def async_by_key(self, geo_object_key: str) -> MeteoERadarLocation:
        """Risolve una localita' dal suo geoObjectKey."""
        payload = await self._get_app(
            PATH_GEOKEYCODING, {"geoObjectKey": geo_object_key}
        )
        if not isinstance(payload, list) or not payload:
            raise MeteoERadarNoResultsError(
                f"geoObjectKey sconosciuto: {geo_object_key}"
            )
        return MeteoERadarLocation.from_placemark(payload[0])

    # -- Dati meteo ------------------------------------------------------------

    def _grid_params(self, location: MeteoERadarLocation) -> dict[str, Any]:
        params: dict[str, Any] = {
            "timezone": location.timezone,
            "location_id": location.location_id,
        }
        if location.grid_latitude and location.grid_longitude:
            params["grid_latitude"] = location.grid_latitude
            params["grid_longitude"] = location.grid_longitude
        return params

    async def async_get_daily(self, location: MeteoERadarLocation) -> dict[str, Any]:
        """Previsione giornaliera a 14 giorni (con 4 dayparts per giorno)."""
        return await self._get_web(PATH_FORECAST, self._grid_params(location))

    async def async_get_shortcast(
        self, location: MeteoERadarLocation
    ) -> dict[str, Any]:
        """Condizioni attuali + 49 ore di previsione oraria."""
        params = self._grid_params(location)
        params.update(
            {
                "language": self._language,
                "latitude": _round_to(location.latitude, 0.00375),
                "longitude": _round_to(location.longitude, 0.01125),
            }
        )
        if location.astro_latitude and location.astro_longitude:
            params["astro_latitude"] = location.astro_latitude
            params["astro_longitude"] = location.astro_longitude
        if location.altitude is not None:
            params["altitude"] = str(int(round(location.altitude / 50.0)) * 50)
        return await self._get_web(PATH_SHORTCAST, params)

    async def async_get_astro(self, location: MeteoERadarLocation) -> dict[str, Any]:
        """Alba/tramonto e fasi lunari (non usato dall'entita' weather)."""
        return await self._get_web(
            PATH_ASTRO,
            {
                "latitude": location.astro_latitude or location.latitude,
                "longitude": location.astro_longitude or location.longitude,
                "timezone": location.timezone,
            },
        )

    async def async_get_aqi(self, location: MeteoERadarLocation) -> dict[str, Any] | None:
        """Indice europeo di qualita' dell'aria (1-6).

        Restituisce ``None`` dove il servizio non copre la localita': in quel
        caso il backend risponde ``204 No Content``.
        """
        return await self._get_web(
            PATH_AQI,
            {
                "language": self._language,
                "timezone": location.timezone,
                "location_id": location.location_id,
            },
        )

    async def async_get_pollen(
        self, location: MeteoERadarLocation
    ) -> dict[str, Any] | None:
        """Carico pollinico a 7 giorni.

        Richiede ``isoCountryCode`` (senza, il backend risponde ``400``) e
        copre solo alcuni paesi europei; altrove risponde ``204``.
        I nomi degli allergeni sono richiesti in inglese perche' facciano da
        chiave stabile per gli entity_id.
        """
        if not location.iso_country_code:
            return None
        return await self._get_web(
            PATH_POLLEN,
            {
                "language": POLLEN_LANGUAGE,
                "timezone": location.timezone,
                "location_id": location.location_id,
                "isoCountryCode": location.iso_country_code,
            },
        )

    async def async_get_all(self, location: MeteoERadarLocation) -> dict[str, Any]:
        """Recupera in parallelo tutti i dati della localita'.

        Previsione e shortcast sono obbligatori e propagano l'eccezione;
        qualita' dell'aria e pollini sono opzionali — non tutte le localita'
        sono coperte — e in caso di errore diventano ``None``, lasciando al
        coordinator il compito di conservare l'ultimo valore noto.
        """
        daily, shortcast, aqi, pollen = await asyncio.gather(
            self.async_get_daily(location),
            self.async_get_shortcast(location),
            self.async_get_aqi(location),
            self.async_get_pollen(location),
            return_exceptions=True,
        )

        for result in (daily, shortcast):
            if isinstance(result, BaseException):
                raise result

        for name, result in (("aqi", aqi), ("pollen", pollen)):
            if isinstance(result, BaseException):
                _LOGGER.debug(
                    "Dati opzionali '%s' non disponibili per %s: %s",
                    name,
                    location.name,
                    result,
                )

        return {
            "daily": daily,
            "shortcast": shortcast,
            "aqi": None if isinstance(aqi, BaseException) else aqi,
            "pollen": None if isinstance(pollen, BaseException) else pollen,
        }
