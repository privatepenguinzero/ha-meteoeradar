"""Sensori separati per Meteo e Radar.

L'impostazione segue le integrazioni meteo di Home Assistant (AccuWeather,
OpenWeatherMap, Tomorrow.io): una ``SensorEntityDescription`` per grandezza,
nomi tradotti via ``translation_key``, e i sensori piu' di nicchia disabilitati
di default per non riempire il registro.

Gli entity_id vengono assegnati esplicitamente nella forma
``sensor.meteoeradar_<localita>_<chiave>`` invece di essere derivati dal nome
tradotto: cosi' restano stabili e prevedibili qualunque sia la lingua di Home
Assistant. Per i pollini questo e' anche cio' che rende possibile scrivere un
adapter per pollenprognos-card, che riconosce le integrazioni dal pattern
dell'entity_id.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    EntityCategory,
    UnitOfLength,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import ATTRIBUTION, DOMAIN, MANUFACTURER, POLLEN_LEVELS, POLLEN_TYPES
from .coordinator import MeteoERadarCoordinator
from .symbols import ALL_CONDITIONS


def _current(data: dict[str, Any]) -> dict[str, Any]:
    return (data or {}).get("current") or {}


def _today(data: dict[str, Any]) -> dict[str, Any]:
    daily = (data or {}).get("daily") or []
    return daily[0] if daily else {}


def _first_hour(data: dict[str, Any]) -> dict[str, Any]:
    hourly = (data or {}).get("hourly") or []
    return hourly[0] if hourly else {}


def _visibility(data: dict[str, Any]) -> Any:
    """Le condizioni attuali non riportano la visibilita': usa la prima ora."""
    value = _current(data).get("visibility")
    if value is None:
        value = _first_hour(data).get("visibility")
    return value


def _location_slug(name: str) -> str:
    """Slug corto della localita': "Roma (Lazio, Italia)" -> "roma"."""
    return slugify(name.split("(")[0].strip()) or "location"


@dataclass(frozen=True, kw_only=True)
class MeteoERadarSensorDescription(SensorEntityDescription):
    """Descrizione di un sensore, con la funzione che ne estrae il valore."""

    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


SENSORS: tuple[MeteoERadarSensorDescription, ...] = (
    # --- condizioni attuali ---------------------------------------------------
    MeteoERadarSensorDescription(
        key="condition",
        translation_key="condition",
        device_class=SensorDeviceClass.ENUM,
        options=list(ALL_CONDITIONS),
        value_fn=lambda data: _current(data).get("condition"),
        attrs_fn=lambda data: {
            "symbol": _current(data).get("symbol"),
            "weather_condition_image": _current(data).get("weather_condition_image"),
        },
    ),
    MeteoERadarSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _current(data).get("temperature"),
    ),
    MeteoERadarSensorDescription(
        key="apparent_temperature",
        translation_key="apparent_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _current(data).get("apparent_temperature"),
    ),
    MeteoERadarSensorDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _current(data).get("humidity"),
    ),
    MeteoERadarSensorDescription(
        key="dew_point",
        translation_key="dew_point",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _current(data).get("dew_point"),
    ),
    MeteoERadarSensorDescription(
        key="pressure",
        translation_key="pressure",
        device_class=SensorDeviceClass.ATMOSPHERIC_PRESSURE,
        native_unit_of_measurement=UnitOfPressure.HPA,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _current(data).get("pressure"),
    ),
    MeteoERadarSensorDescription(
        key="pressure_tendency",
        translation_key="pressure_tendency",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: _current(data).get("pressure_tendency"),
    ),
    MeteoERadarSensorDescription(
        key="wind_speed",
        translation_key="wind_speed",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _current(data).get("wind_speed"),
    ),
    MeteoERadarSensorDescription(
        key="wind_gust_speed",
        translation_key="wind_gust_speed",
        device_class=SensorDeviceClass.WIND_SPEED,
        native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _current(data).get("wind_gust_speed"),
    ),
    MeteoERadarSensorDescription(
        key="wind_bearing",
        translation_key="wind_bearing",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _current(data).get("wind_bearing"),
    ),
    MeteoERadarSensorDescription(
        key="visibility",
        translation_key="visibility",
        device_class=SensorDeviceClass.DISTANCE,
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_visibility,
    ),
    MeteoERadarSensorDescription(
        key="cloud_cover",
        translation_key="cloud_cover",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        # Dedotto dalla classe del simbolo (0/15/30/60/100 %), non misurato.
        value_fn=lambda data: _current(data).get("cloud_cover"),
    ),
    MeteoERadarSensorDescription(
        key="precipitation_probability",
        translation_key="precipitation_probability",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _current(data).get("precipitation_probability"),
    ),
    MeteoERadarSensorDescription(
        key="precipitation_type",
        translation_key="precipitation_type",
        entity_registry_enabled_default=False,
        value_fn=lambda data: _current(data).get("precipitation_type"),
    ),
    MeteoERadarSensorDescription(
        key="smog_level",
        translation_key="smog_level",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: _current(data).get("smog_level"),
    ),
    MeteoERadarSensorDescription(
        key="solar_elevation",
        translation_key="solar_elevation",
        native_unit_of_measurement=DEGREE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: _current(data).get("solar_elevation"),
    ),
    # --- previsione di oggi ---------------------------------------------------
    MeteoERadarSensorDescription(
        key="temperature_max",
        translation_key="temperature_max",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: _today(data).get("temperature"),
    ),
    MeteoERadarSensorDescription(
        key="temperature_min",
        translation_key="temperature_min",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda data: _today(data).get("templow"),
    ),
    MeteoERadarSensorDescription(
        key="uv_index",
        translation_key="uv_index",
        value_fn=lambda data: _today(data).get("uv_index"),
    ),
    MeteoERadarSensorDescription(
        key="precipitation_today",
        translation_key="precipitation_today",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=UnitOfPrecipitationDepth.MILLIMETERS,
        value_fn=lambda data: _today(data).get("precipitation"),
    ),
    MeteoERadarSensorDescription(
        key="sunshine_duration",
        translation_key="sunshine_duration",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        value_fn=lambda data: _today(data).get("sunshine_hours"),
    ),
)

# Creato solo dove il servizio copre la localita'.
AQI_SENSOR = MeteoERadarSensorDescription(
    key="air_quality_index",
    translation_key="air_quality_index",
    device_class=SensorDeviceClass.AQI,
    value_fn=lambda data: ((data or {}).get("aqi") or {}).get("index"),
    attrs_fn=lambda data: {
        "description": ((data or {}).get("aqi") or {}).get("text"),
        "color": ((data or {}).get("aqi") or {}).get("color"),
        "source": ((data or {}).get("aqi") or {}).get("source"),
    },
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Crea i sensori disponibili per la localita'."""
    coordinator: MeteoERadarCoordinator = entry.runtime_data
    data = coordinator.data or {}

    entities: list[SensorEntity] = [
        MeteoERadarSensor(coordinator, entry, description, hass)
        for description in SENSORS
    ]

    if (data.get("aqi") or {}).get("index") is not None:
        entities.append(MeteoERadarSensor(coordinator, entry, AQI_SENSOR, hass))

    pollen = (data.get("pollen") or {}).get("types") or {}
    for allergen in POLLEN_TYPES:
        if allergen in pollen:
            entities.append(MeteoERadarPollenSensor(coordinator, entry, allergen, hass))

    async_add_entities(entities)


class MeteoERadarSensorBase(CoordinatorEntity[MeteoERadarCoordinator], SensorEntity):
    """Base comune: device condiviso ed entity_id esplicito."""

    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MeteoERadarCoordinator,
        entry: ConfigEntry,
        object_id_suffix: str,
        hass: HomeAssistant,
    ) -> None:
        super().__init__(coordinator)
        location = coordinator.location
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=location.name,
            manufacturer=MANUFACTURER,
            model="Previsioni meteoeradar.it",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://www.meteoeradar.it/",
        )
        self.entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT,
            f"{DOMAIN}_{_location_slug(location.name)}_{object_id_suffix}",
            hass=hass,
        )


class MeteoERadarSensor(MeteoERadarSensorBase):
    """Sensore descritto da una MeteoERadarSensorDescription."""

    entity_description: MeteoERadarSensorDescription

    def __init__(
        self,
        coordinator: MeteoERadarCoordinator,
        entry: ConfigEntry,
        description: MeteoERadarSensorDescription,
        hass: HomeAssistant,
    ) -> None:
        super().__init__(coordinator, entry, description.key, hass)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}-{description.key}"

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data or {})


class MeteoERadarPollenSensor(MeteoERadarSensorBase):
    """Carico pollinico odierno per un allergene (scala 0-3).

    L'entity_id usa lo slug inglese dell'allergene
    (``sensor.meteoeradar_<localita>_<allergene>``), la stessa forma che
    l'integrazione polleninformation espone e che pollenprognos-card
    riconosce dal pattern.
    """

    def __init__(
        self,
        coordinator: MeteoERadarCoordinator,
        entry: ConfigEntry,
        allergen: str,
        hass: HomeAssistant,
    ) -> None:
        super().__init__(coordinator, entry, allergen, hass)
        self._allergen = allergen
        self._attr_unique_id = f"{entry.entry_id}-pollen-{allergen}"
        # Una chiave di traduzione per allergene: il nome mostrato e' tradotto,
        # mentre l'entity_id resta sullo slug inglese.
        self._attr_translation_key = f"pollen_{allergen}"

    @property
    def _pollen_entry(self) -> dict[str, Any]:
        pollen = (self.coordinator.data or {}).get("pollen") or {}
        return (pollen.get("types") or {}).get(self._allergen) or {}

    @property
    def native_value(self) -> int | None:
        return self._pollen_entry.get("value")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        pollen = (self.coordinator.data or {}).get("pollen") or {}
        return {
            "allergen": self._allergen,
            "level": self._pollen_entry.get("level"),
            "level_max": max(POLLEN_LEVELS),
            "date": pollen.get("date"),
        }
