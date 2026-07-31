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

DEFAULT_LANGUAGE: Final = "it"
DEFAULT_UPDATE_MINUTES: Final = 15
MIN_UPDATE_MINUTES: Final = 5
MAX_UPDATE_MINUTES: Final = 120
DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=DEFAULT_UPDATE_MINUTES)

REQUEST_TIMEOUT: Final = 30
