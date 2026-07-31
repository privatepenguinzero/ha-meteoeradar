"""Costanti per l'integrazione Meteo e Radar (meteoeradar.it)."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "meteoeradar"
MANUFACTURER: Final = "Meteo e Radar"
ATTRIBUTION: Final = "Dati forniti da meteoeradar.it (WetterOnline)"

# --- Endpoint estratti dal bundle Angular di https://www.meteoeradar.it ---------
#
# Il sito espone due backend distinti, entrambi autenticati tramite un token
# statico passato nel parametro di query `c` (base64 di "utente:password").
# Il token NON deve essere URL-encoded: i caratteri `=` finali vanno inviati
# letterali, altrimenti il backend risponde 401.
#
#   apiapp   -> https://api-app.wetteronline.de/   (ricerca geografica)
#               parametri fissi: av=2, c=<APP_API_TOKEN>
#   apicloud -> https://api-web.wo-cloud.com/      (dati meteo "blending")
#               parametri fissi: c=<WEB_API_TOKEN>

APP_API_BASE: Final = "https://api-app.wetteronline.de"
APP_API_TOKEN: Final = "cHdhOnNCcDlyQnprcHhrOTMrPWA="  # base64("pwa:...")
APP_API_VERSION: Final = "2"
APP_APPLICATION: Final = "pwa"

WEB_API_BASE: Final = "https://api-web.wo-cloud.com"
WEB_API_TOKEN: Final = "d293ZWI6QzhMNFRINmVUbkRoVWFqYg=="  # base64("woweb:...")

PATH_GEOCODING: Final = "search/geocoding"
PATH_REVERSE_GEOCODING: Final = "search/reversegeocoding"
PATH_GEOKEYCODING: Final = "search/geokeycoding"
PATH_FORECAST: Final = "blending/forecast/v1"
PATH_SHORTCAST: Final = "blending/shortcast/v1"
PATH_ASTRO: Final = "astro/days/v1"
PATH_AQI: Final = "aqi/v1"
PATH_POLLEN: Final = "pollen/v4"

# Header inviati dal sito: senza Referer alcuni edge node rispondono 403.
DEFAULT_HEADERS: Final = {
    "Accept": "application/json",
    "Origin": "https://www.meteoeradar.it",
    "Referer": "https://www.meteoeradar.it/",
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
}

# --- Configurazione ------------------------------------------------------------

CONF_MODE: Final = "mode"
CONF_QUERY: Final = "query"
CONF_LOCATION: Final = "location"
CONF_LANGUAGE: Final = "language"
CONF_UPDATE_INTERVAL: Final = "update_interval"

MODE_HOME: Final = "home"
MODE_SEARCH: Final = "search"

# Chiavi della localita' memorizzate nella config entry (evitano di ri-geocodificare).
LOC_KEY: Final = "geo_object_key"
LOC_NAME: Final = "name"
LOC_LATITUDE: Final = "latitude"
LOC_LONGITUDE: Final = "longitude"
LOC_ALTITUDE: Final = "altitude"
LOC_TIMEZONE: Final = "timezone"
LOC_LOCATION_ID: Final = "location_id"
LOC_GRID_LATITUDE: Final = "grid_latitude"
LOC_GRID_LONGITUDE: Final = "grid_longitude"
LOC_ASTRO_LATITUDE: Final = "astro_latitude"
LOC_ASTRO_LONGITUDE: Final = "astro_longitude"
LOC_ISO_COUNTRY: Final = "iso_country_code"

# "auto" segue la lingua di Home Assistant. Il backend tollera qualunque codice
# e ripiega sull'inglese per quelli che non conosce, quindi non serve una
# whitelist: le opzioni esplicite servono solo a forzare una lingua diversa.
LANGUAGE_AUTO: Final = "auto"
LANGUAGE_OPTIONS: Final[tuple[str, ...]] = (LANGUAGE_AUTO, "it", "en")
FALLBACK_LANGUAGE: Final = "en"

# Regione predefinita per lingua, usata solo quando Home Assistant non ha un
# paese configurato. Il parametro `region` orienta la ricerca geografica:
# cercare "Milano" con region=GB restituisce una localita' in Texas.
LANGUAGE_REGIONS: Final[dict[str, str]] = {
    "it": "IT",
    "en": "GB",
    "de": "DE",
    "fr": "FR",
    "es": "ES",
    "nl": "NL",
    "pl": "PL",
    "pt": "PT",
    "cs": "CZ",
    "sk": "SK",
    "hu": "HU",
    "ro": "RO",
    "bg": "BG",
    "hr": "HR",
    "sl": "SI",
    "uk": "UA",
    "el": "GR",
    "tr": "TR",
    "da": "DK",
}

DEFAULT_LANGUAGE: Final = LANGUAGE_AUTO

# I pollini vengono sempre richiesti in inglese: i nomi restituiti sono slug
# canonici ("grasses", "birch", "ragweed"…) e servono da chiave stabile per gli
# entity_id. Il nome mostrato all'utente arriva dalle traduzioni.
POLLEN_LANGUAGE: Final = "en"

# Vocabolario completo osservato su IT, DE, AT, CH, FR, ES, NL, PL.
POLLEN_TYPES: Final[tuple[str, ...]] = (
    "alder",
    "ash",
    "beech",
    "birch",
    "chestnut",
    "cypress",
    "elm",
    "goosefoot",
    "grasses",
    "hazel",
    "hornbeam",
    "linden",
    "mugwort",
    "nettle",
    "oak",
    "olive",
    "pellitory",
    "pine",
    "plane",
    "plantain",
    "poplar",
    "ragweed",
    "rumex",
    "rye",
    "willow",
)

# Scala di carico pollinico usata dal backend.
POLLEN_LEVELS: Final[dict[int, str]] = {
    0: "none",
    1: "low",
    2: "moderate",
    3: "high",
}
DEFAULT_UPDATE_MINUTES: Final = 15
MIN_UPDATE_MINUTES: Final = 5
MAX_UPDATE_MINUTES: Final = 120
DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=DEFAULT_UPDATE_MINUTES)

REQUEST_TIMEOUT: Final = 30
