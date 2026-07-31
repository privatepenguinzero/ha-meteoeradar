"""Coordinator: scarica e normalizza i dati di meteoeradar.it."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MeteoERadarClient, MeteoERadarError, MeteoERadarLocation
from .const import DOMAIN, POLLEN_LEVELS
from .symbols import cloud_cover_percent, is_night, to_condition

_LOGGER = logging.getLogger(__name__)


def _num(value: Any) -> float | None:
    """Converte in float i valori numerici restituiti come stringa.

    Il backend usa spesso stringhe e talvolta intervalli ("3-4" per i Beaufort):
    in quel caso si prende l'estremo superiore, che e' il valore mostrato dal
    sito come "fino a".
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    if "-" in text[1:]:
        text = text.rsplit("-", 1)[-1]
    try:
        return float(text)
    except ValueError:
        return None


def _percent(value: Any) -> int | None:
    """Le frazioni 0..1 dell'API diventano percentuali 0..100."""
    number = _num(value)
    if number is None:
        return None
    return int(round(number * 100))


def _temperature(block: Any, key: str | None = None) -> float | None:
    """Estrae i gradi Celsius da un blocco temperatura."""
    if not isinstance(block, dict):
        return None
    if key is not None:
        block = block.get(key)
        if not isinstance(block, dict):
            return None
    return _num(block.get("celsius"))


def _interval_mean(interval: Any) -> float | None:
    if not isinstance(interval, dict):
        return _num(interval)
    begin = _num(interval.get("interval_begin"))
    end = _num(interval.get("interval_end"))
    if begin is None and end is None:
        return None
    if begin is None:
        return end
    if end is None:
        return begin
    return round((begin + end) / 2.0, 2)


def _precipitation_mm(precipitation: Any) -> float | None:
    """Quantita' di precipitazione in mm.

    ``details`` compare solo quando e' attesa precipitazione e riporta un
    intervallo (``interval_begin`` / ``interval_end``): si usa il valore medio.
    La neve e' espressa in centimetri di altezza e viene convertita in mm.
    """
    if not isinstance(precipitation, dict):
        return None
    details = precipitation.get("details")
    if not isinstance(details, dict):
        return 0.0

    rainfall = details.get("rainfall_amount")
    if isinstance(rainfall, dict):
        value = _interval_mean(rainfall.get("millimeter"))
        if value is not None:
            return value

    snow = details.get("snow_height")
    if isinstance(snow, dict):
        value = _interval_mean(snow.get("centimeter"))
        if value is not None:
            return round(value * 10.0, 1)

    return 0.0


def _wind(block: Any) -> dict[str, float | None]:
    """Velocita' (km/h), raffica (km/h) e direzione (gradi)."""
    if not isinstance(block, dict):
        return {"speed": None, "gust": None, "bearing": None}
    speeds = (block.get("speed") or {}).get("kilometer_per_hour") or {}
    return {
        "speed": _num(speeds.get("value")),
        "gust": _num(speeds.get("max_gust")),
        "bearing": _num(block.get("direction")),
    }


def _parse_common(entry: dict[str, Any]) -> dict[str, Any]:
    """Campi condivisi tra ora corrente, ore e giorni."""
    wind = _wind(entry.get("wind"))
    precipitation = entry.get("precipitation")
    visibility = entry.get("visibility") or {}
    meters = _num(visibility.get("meter"))

    return {
        "datetime": entry.get("date"),
        "symbol": entry.get("symbol"),
        "condition": to_condition(entry.get("symbol")),
        "is_night": is_night(entry.get("symbol")),
        "cloud_cover": cloud_cover_percent(entry.get("symbol")),
        "smog_level": entry.get("smog_level"),
        "humidity": _percent(entry.get("humidity")),
        "pressure": _num((entry.get("air_pressure") or {}).get("hpa")),
        "dew_point": _temperature(entry.get("dew_point")),
        "precipitation": _precipitation_mm(precipitation),
        "precipitation_probability": _percent((precipitation or {}).get("probability")),
        "precipitation_type": (precipitation or {}).get("type"),
        "wind_speed": wind["speed"],
        "wind_gust_speed": wind["gust"],
        "wind_bearing": wind["bearing"],
        "visibility": round(meters / 1000.0, 1) if meters is not None else None,
    }


def _parse_current(entry: dict[str, Any]) -> dict[str, Any]:
    data = _parse_common(entry)
    data.update(
        {
            "temperature": _temperature(entry.get("air_temperature")),
            "apparent_temperature": _temperature(entry.get("apparent_temperature")),
            "weather_condition_image": entry.get("weather_condition_image"),
            "solar_elevation": _num(entry.get("solar_elevation")),
            "pressure_tendency": entry.get("air_pressure_tendency_category"),
        }
    )
    return data


def _parse_aqi(payload: Any) -> dict[str, Any] | None:
    """Indice europeo di qualita' dell'aria, con testo e colore della scala."""
    if not isinstance(payload, dict):
        return None
    current = payload.get("current")
    if not isinstance(current, dict) or current.get("index") is None:
        return None
    index = _num(current.get("index"))
    scale = payload.get("scale") or {}
    return {
        "index": int(index) if index is not None else None,
        "text": current.get("text"),
        "color": current.get("color"),
        "source": scale.get("source"),
    }


def _parse_pollen(payload: Any) -> dict[str, Any] | None:
    """Carico pollinico odierno, indicizzato per nome canonico inglese."""
    if not isinstance(payload, dict):
        return None
    days = payload.get("days")
    if not isinstance(days, list) or not days:
        return None

    today = days[0]
    if not isinstance(today, dict):
        return None

    levels: dict[str, dict[str, Any]] = {}
    for item in today.get("pollen") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip().lower()
        value = _num(item.get("value"))
        if not name or value is None:
            continue
        levels[name] = {
            "value": int(value),
            "level": POLLEN_LEVELS.get(int(value)),
        }

    if not levels:
        return None

    max_burden = today.get("max_burden") or {}
    max_value = _num(max_burden.get("value"))
    return {
        "date": today.get("date"),
        "types": levels,
        "max_name": str(max_burden.get("name") or "").strip().lower() or None,
        "max_value": int(max_value) if max_value is not None else None,
    }


def _parse_hour(entry: dict[str, Any]) -> dict[str, Any]:
    data = _parse_common(entry)
    data.update(
        {
            "temperature": _temperature(entry.get("air_temperature")),
            "apparent_temperature": _temperature(entry.get("apparent_temperature")),
        }
    )
    return data


def _parse_day(entry: dict[str, Any]) -> dict[str, Any]:
    data = _parse_common(entry)
    uv_index = entry.get("uv_index") or {}
    data.update(
        {
            "temperature": _temperature(entry.get("air_temperature"), "max"),
            "templow": _temperature(entry.get("air_temperature"), "min"),
            "apparent_temperature": _temperature(
                entry.get("apparent_temperature"), "max"
            ),
            "uv_index": _num(uv_index.get("value")),
            "sunshine_hours": _num((entry.get("sunshine_duration") or {}).get("hours")),
        }
    )
    return data


class MeteoERadarCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Aggiorna periodicamente i dati di una localita'."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: MeteoERadarClient,
        location: MeteoERadarLocation,
        update_interval: timedelta,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} {location.name}",
            update_interval=update_interval,
            config_entry=entry,
        )
        self.client = client
        self.location = location

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            payload = await self.client.async_get_all(self.location)
        except MeteoERadarError as err:
            raise UpdateFailed(str(err)) from err

        shortcast = payload.get("shortcast") or {}
        daily = payload.get("daily") or {}

        current_raw = shortcast.get("current")
        if not isinstance(current_raw, dict):
            raise UpdateFailed("Risposta shortcast priva delle condizioni attuali")

        previous = self.data or {}
        aqi = _parse_aqi(payload.get("aqi"))
        pollen = _parse_pollen(payload.get("pollen"))

        return {
            "current": _parse_current(current_raw),
            "hourly": [
                _parse_hour(hour)
                for hour in shortcast.get("hours") or []
                if isinstance(hour, dict)
            ],
            "daily": [
                _parse_day(day)
                for day in daily.get("days") or []
                if isinstance(day, dict)
            ],
            # Qualita' dell'aria e pollini non coprono tutte le localita' e
            # possono fallire indipendentemente dal meteo: se mancano si tiene
            # l'ultimo valore noto invece di far sparire i sensori.
            "aqi": aqi if aqi is not None else previous.get("aqi"),
            "pollen": pollen if pollen is not None else previous.get("pollen"),
        }
