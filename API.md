# API di meteoeradar.it — note di reverse engineering

Documentazione ricavata dal bundle Angular di `https://www.meteoeradar.it`
(`main.<hash>.js`) e verificata con chiamate reali. `meteoeradar.it` è la
versione italiana della piattaforma WetterOnline: gli stessi endpoint servono
tutti i domini gemelli (`weatherandradar.com`, `wetteronline.de`,
`tiempoyradar.es`, …).

## Autenticazione

Non c'è OAuth né API key personale. Ogni backend accetta un token statico
passato nel parametro di query `c`, che è il base64 di `utente:password`:

| Backend | Base URL | Token `c` | Parametri fissi |
|---|---|---|---|
| `apiapp` | `https://api-app.wetteronline.de/` | `cHdhOnNCcDlyQnprcHhrOTMrPWA=` | `av=2` |
| `apicloud` | `https://api-web.wo-cloud.com/` | `d293ZWI6QzhMNFRINmVUbkRoVWFqYg==` | — |

> **Attenzione**: il token va inviato **non** URL-encoded. Se gli `=` finali
> arrivano come `%3D` il backend risponde `401`.

Header consigliati (il sito li invia sempre; alcuni edge node rifiutano senza
`Referer`):

```
Origin:  https://www.meteoeradar.it
Referer: https://www.meteoeradar.it/
```

Altri endpoint dichiarati nel bundle, non usati da questa integrazione:

| Nome | URL |
|---|---|
| `contentapi` | `https://api.wo-cloud.com/content/` |
| `radartiles` | `https://tiles.wo-cloud.com/` |
| `radar` | `https://radar.wo-cloud.com/pwa/` |
| `geo` | `https://search.prod.geo.wo-cloud.com/` |
| `pastdata` | `https://api.wo-cloud.com/content/past-data/` |
| fulmini realtime | `wss://realtime.tiles.wo-cloud.com` (WebSocket) |
| tile radar | `https://tiles.wo-cloud.com/snippet-tiles` |
| bounds per paese | `https://tiles.wo-cloud.com/country-radar-bounds/{iso}` |

## 1. Ricerca geografica

Serve a ottenere le chiavi (`location_id`, griglia nowcast/astro) necessarie a
tutte le chiamate meteo.

### `GET /search/geocoding` — ricerca per nome

```
https://api-app.wetteronline.de/search/geocoding
  ?name=Roma
  &language=it
  &region=IT
  &application=pwa
  &mv=10
  &av=2
  &c=cHdhOnNCcDlyQnprcHhrOTMrPWA=
```

Risposta `200` con array di un elemento (la corrispondenza migliore) oppure
`204 No Content` se non trova nulla.

```json
[{
  "geoObject": {
    "displayName": { "primaryName": "Roma", "secondaryNames": ["Lazio", "Italia"] },
    "locationName": "Roma",
    "latitude": 41.8919, "longitude": 12.5113, "altitude": 20,
    "timeZone": "Europe/Rome",
    "geoObjectKey": "8758219",
    "iso-3166-1": "IT"
  },
  "contentKeys": {
    "forecastKey": { "location_id": "16242" },
    "aqiKey":      { "location_id": "16242" },
    "pollenKey":   { "location_id": "16242" },
    "nowcastKey":  { "woGridKey": { "gridLatitude": "41.88", "gridLongitude": "12.48" } },
    "astroKey":    { "woGridKey": { "gridLatitude": "41.88", "gridLongitude": "12.48" } }
  }
}]
```

### `GET /search/reversegeocoding` — ricerca per coordinate

Stessi parametri base più `latitude`, `longitude` e opzionalmente `altitude`.
Il frontend arrotonda prima di chiamare: latitudine a multipli di `0.02`,
longitudine a `0.016`, altitudine a `50` metri.

### `GET /search/geokeycoding` — ricerca per `geoObjectKey`

Parametro `geoObjectKey=<chiave>`. Utile per ricostruire una località salvata.

### `GET /search/topcities`

Elenco delle città principali per la regione richiesta.

## 2. Dati meteo (`apicloud`)

Tutti gli endpoint "blending" accettano `timezone` e `location_id`; se la
località ha una `nowcastKey` si aggiungono `grid_latitude` e `grid_longitude`,
che migliorano la precisione locale.

### `GET /blending/forecast/v1` — 14 giorni

```
https://api-web.wo-cloud.com/blending/forecast/v1
  ?timezone=Europe/Rome
  &location_id=16242
  &grid_latitude=41.88
  &grid_longitude=12.48
  &c=d293ZWI6QzhMNFRINmVUbkRoVWFqYg==
```

```json
{
  "days": [{
    "date": "2026-07-31T00:00:00+02:00",
    "symbol": "so____",
    "air_temperature":      { "max": { "celsius": 37 }, "min": { "celsius": 25 } },
    "apparent_temperature": { "max": { "celsius": 37 }, "min": { "celsius": 25 } },
    "air_pressure": { "hpa": "1014", "inhg": 29.94, "mmhg": "761" },
    "humidity": 0.45,
    "precipitation": { "probability": 0.05, "type": "rain" },
    "uv_index": { "value": 8, "description": "very_high" },
    "sunshine_duration": { "hours": 14 },
    "significant_weather_index": "none",
    "smog_level": "none",
    "wind": { "direction": 265, "speed": { "kilometer_per_hour": { "value": "20", "max_gust": "45" } } },
    "dayparts": [ { "type": "afternoon", "date": "...", "…": "stessi campi, valore singolo" } ],
    "dayhalves": { "daytime": {}, "nighttime": {} }
  }],
  "meta": {}
}
```

Quando è prevista precipitazione, `precipitation` guadagna un blocco `details`:

```json
"precipitation": {
  "probability": 0.7,
  "type": "rain",
  "details": {
    "duration": { "hours": "3" },
    "probability": 0.7,
    "rainfall_amount": {
      "millimeter": { "interval_begin": 5.0, "interval_end": 10.0 },
      "inch":       { "interval_begin": 0.2, "interval_end": 0.5 }
    }
  }
}
```

Per la neve compare `snow_height` (in `centimeter`) al posto di
`rainfall_amount`. Se `details` è assente non è prevista precipitazione
misurabile.

### `GET /blending/shortcast/v1` — condizioni attuali + 49 ore

Parametri: quelli di `forecast/v1` più `language`, `latitude`, `longitude` e,
se disponibili, `astro_latitude` / `astro_longitude` e `altitude`.
Le coordinate vengono arrotondate dal frontend a `0.00375` (lat) e `0.01125` (lon).

```json
{
  "current": {
    "date": "2026-07-31T11:20:43+02:00",
    "symbol": "so____",
    "weather_condition_image": "sunny",
    "air_temperature": { "celsius": 35 },
    "apparent_temperature": { "celsius": 36 },
    "dew_point": { "celsius": 15 },
    "humidity": 0.3,
    "air_pressure": { "hpa": "1015" },
    "air_pressure_tendency_category": 0,
    "precipitation": { "probability": 0.0, "type": "rain" },
    "solar_elevation": 55.8,
    "wind": { "direction": 360, "speed": { "kilometer_per_hour": { "value": "10", "max_gust": "20" } } }
  },
  "hours": [{
    "date": "2026-07-31T12:00:00+02:00",
    "symbol": "so____",
    "air_temperature": { "celsius": 36 },
    "convection_probability": 0.8,
    "visibility": { "meter": 30000, "feet": 98425 },
    "precipitation": { "probability": 0.0, "type": "rain" },
    "…": "come sopra"
  }],
  "meta": { "item_invalidations": { "hours": { "max_items_to_display": 49 } } }
}
```

`blending/current/v2` esiste ma restituisce un sottoinsieme di `current`
(temperatura, simbolo, raffiche): `shortcast` lo rende superfluo.

### Altri endpoint `apicloud`

| Path | Parametri | Contenuto |
|---|---|---|
| `astro/days/v1` | `latitude`, `longitude`, `timezone` | alba/tramonto, sorgere/tramontare ed età della luna |
| `aqi/v1` | `language`, `timezone`, `location_id` | indice di qualità dell'aria |
| `blending/uv-index/v1` | `timezone`, `location_id` | indice UV giornaliero con scala |
| `pollen/v4` | `timezone`, `language`, `location_id`, `isoCountryCode` | pollini |
| `blending/texts/v1/one_day` | vari | testo descrittivo della giornata |
| `blending/mountain/forecast/v1` | come `forecast/v1` | previsione per aree montane |
| `symbolmap/data/v3/maps` | `map_id`, `language`, `unit` | mappe dei simboli |
| `warnings/maps/v4/` | `isoCountryCode` | allerte meteo |

## 3. Codici simbolo

Il campo `symbol` è una stringa di 6 caratteri riempita a destra con `_`.
Il bundle contiene sia l'elenco completo dei **166** codici validi
(`Y.symbols = [...]`) sia una tabella `{regex, data}` usata per lo sfondo
dinamico, che ne rivela la semantica:

```js
{ regex: /bd[rs]3/, data: { cloudy: 1.0, rain: 1.0, snow: 0, freezing: 0,
                            lightning: 0, wind: 0.3, sightDistance: 750 } }
```

### Grammatica

```
[ base 2 char ][ fenomeno + intensità 0-4 char ]
```

**Base** — copertura nuvolosa e giorno/notte:

| Base giorno | Base notte | `cloudy` | Significato |
|---|---|---|---|
| `so` | `mo` | 0.00 | sereno |
| `ms` | `mm` | 0.15 | poco nuvoloso |
| `wb` | `mb` | 0.30 | parzialmente nuvoloso |
| `bw` | `mw` | 0.60 | nuvoloso |
| `bd` | `md` | 1.00 | coperto |
| `ns` `as` `cs` `nb` `ap` `ca` | `nm` `am` `cm` `nn` `an` `cn` | — | nebbia (`sightDistance` 50–500) |

**Suffisso** — fenomeno e intensità (`1` debole → `3` forte):

| Suffisso | Fenomeno |
|---|---|
| *(vuoto)* | nessuna precipitazione |
| `r1 r2 r3` | pioggia |
| `s1 s2 s3` | rovesci |
| `sn1..3`, `sns1..3` | neve, rovesci di neve |
| `sr1..3`, `srs1..3` | neve mista a pioggia |
| `g1 g2 g3` | temporale (`lightning: 1.0`) |
| `sg` | temporale di neve |
| `gr1 gr2` | pioggia che gela (`freezing: 1.0`) |

Esempi: `so____` sereno · `bds1__` coperto con rovesci deboli ·
`mdsns3` coperto notturno con forti rovesci di neve · `wbgr1_` parzialmente
nuvoloso con pioggia che gela.

L'implementazione è in
[`custom_components/meteoeradar/symbols.py`](custom_components/meteoeradar/symbols.py).

## 4. Stabilità

I token sono incorporati nel bundle e cambiano quando WetterOnline ruota le
credenziali. Se l'integrazione comincia a rispondere `401`, basta rileggerli:

```bash
# 1. trova il nome del bundle
curl -s https://www.meteoeradar.it/ \
  | grep -oE '<script[^>]*src="main\.[^"]+"' | sed 's/.*src="//;s/"//'

# 2. scarica il bundle ed estrai i token
curl -s https://www.meteoeradar.it/main.<hash>.js \
  | grep -oE 'c:"[A-Za-z0-9+/=]+"'
```

Poi aggiorna `APP_API_TOKEN` / `WEB_API_TOKEN` in
[`const.py`](custom_components/meteoeradar/const.py).
