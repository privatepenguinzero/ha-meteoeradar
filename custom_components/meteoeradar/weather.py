"""Entita' weather per Meteo e Radar."""

from __future__ import annotations

from typing import Any

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfLength,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, MANUFACTURER
from .coordinator import MeteoERadarCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Crea l'entita' weather per la config entry."""
    coordinator: MeteoERadarCoordinator = entry.runtime_data
    async_add_entities([MeteoERadarWeather(coordinator, entry)])


class MeteoERadarWeather(CoordinatorEntity[MeteoERadarCoordinator], WeatherEntity):
    """Espone i dati di meteoeradar.it come entita' weather di Home Assistant."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True
    _attr_name = None

    # Il backend restituisce sempre anche il sistema metrico: si dichiarano le
    # unita' native corrispondenti e Home Assistant converte se necessario.
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_native_pressure_unit = UnitOfPressure.HPA
    _attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_native_precipitation_unit = UnitOfPrecipitationDepth.MILLIMETERS
    _attr_native_visibility_unit = UnitOfLength.KILOMETERS

    _attr_supported_features = (
        WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY
    )

    def __init__(self, coordinator: MeteoERadarCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        location = coordinator.location
        self._attr_unique_id = f"{entry.entry_id}-weather"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=location.name,
            manufacturer=MANUFACTURER,
            model="Previsioni meteoeradar.it",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.meteoeradar.it/",
        )

    # -- Accesso ai dati -------------------------------------------------------

    @property
    def _current(self) -> dict[str, Any]:
        data = self.coordinator.data or {}
        return data.get("current") or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self._current)

    # -- Condizioni attuali ----------------------------------------------------

    @property
    def condition(self) -> str | None:
        return self._current.get("condition")

    @property
    def native_temperature(self) -> float | None:
        return self._current.get("temperature")

    @property
    def native_apparent_temperature(self) -> float | None:
        return self._current.get("apparent_temperature")

    @property
    def native_dew_point(self) -> float | None:
        return self._current.get("dew_point")

    @property
    def humidity(self) -> float | None:
        return self._current.get("humidity")

    @property
    def native_pressure(self) -> float | None:
        return self._current.get("pressure")

    @property
    def native_wind_speed(self) -> float | None:
        return self._current.get("wind_speed")

    @property
    def native_wind_gust_speed(self) -> float | None:
        return self._current.get("wind_gust_speed")

    @property
    def wind_bearing(self) -> float | None:
        return self._current.get("wind_bearing")

    @property
    def native_visibility(self) -> float | None:
        return self._current.get("visibility")

    @property
    def uv_index(self) -> float | None:
        """UV del giorno corrente: e' disponibile solo nella previsione giornaliera."""
        daily = (self.coordinator.data or {}).get("daily") or []
        if daily:
            return daily[0].get("uv_index")
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Dettagli specifici del provider, utili per template e debug."""
        current = self._current
        return {
            "symbol": current.get("symbol"),
            "weather_condition_image": current.get("weather_condition_image"),
            "precipitation_type": current.get("precipitation_type"),
            "precipitation_probability": current.get("precipitation_probability"),
            "solar_elevation": current.get("solar_elevation"),
            "location": self.coordinator.location.name,
            "location_id": self.coordinator.location.location_id,
        }

    # -- Previsioni ------------------------------------------------------------

    async def async_forecast_daily(self) -> list[Forecast] | None:
        return [
            self._to_forecast(day, daily=True)
            for day in (self.coordinator.data or {}).get("daily") or []
        ]

    async def async_forecast_hourly(self) -> list[Forecast] | None:
        return [
            self._to_forecast(hour, daily=False)
            for hour in (self.coordinator.data or {}).get("hourly") or []
        ]

    @staticmethod
    def _to_forecast(entry: dict[str, Any], *, daily: bool) -> Forecast:
        forecast: Forecast = {
            "datetime": entry.get("datetime"),
            "condition": entry.get("condition"),
            "native_temperature": entry.get("temperature"),
            "native_apparent_temperature": entry.get("apparent_temperature"),
            "humidity": entry.get("humidity"),
            "native_precipitation": entry.get("precipitation"),
            "precipitation_probability": entry.get("precipitation_probability"),
            "native_pressure": entry.get("pressure"),
            "native_wind_speed": entry.get("wind_speed"),
            "native_wind_gust_speed": entry.get("wind_gust_speed"),
            "wind_bearing": entry.get("wind_bearing"),
        }
        if daily:
            forecast["native_templow"] = entry.get("templow")
            forecast["uv_index"] = entry.get("uv_index")
        else:
            forecast["native_dew_point"] = entry.get("dew_point")
        return forecast
