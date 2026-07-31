# Meteo e Radar — provider meteo custom per Home Assistant

Integrazione custom che espone i dati di [meteoeradar.it](https://www.meteoeradar.it)
(brand italiano di WetterOnline) come entità `weather.*` di Home Assistant,
pensata per essere usata con
[clock-weather-card](https://github.com/pkissling/clock-weather-card).

Non esiste una API pubblica documentata: gli endpoint sono stati ricavati dal
bundle JavaScript del sito. I dettagli sono in [API.md](API.md).

## Cosa fornisce

| Dato | Fonte | Copertura |
|---|---|---|
| Condizioni attuali | `blending/shortcast/v1` → `current` | aggiornate al minuto |
| Previsione oraria | `blending/shortcast/v1` → `hours` | 49 ore |
| Previsione giornaliera | `blending/forecast/v1` → `days` | 14 giorni |

L'entità dichiara `FORECAST_DAILY | FORECAST_HOURLY`, quindi funziona sia con
`hourly_forecast: false` sia con `hourly_forecast: true` nella card.

Attributi nativi: temperatura, temperatura percepita, umidità, pressione,
punto di rugiada, velocità e raffica del vento, direzione del vento, visibilità,
indice UV. Nelle previsioni: `native_temperature`, `native_templow`,
`native_precipitation` (mm), `precipitation_probability` (%), `humidity`,
vento e — solo giornaliere — `uv_index`.

Attributi extra specifici del provider: `symbol` (codice WetterOnline grezzo),
`weather_condition_image`, `precipitation_type`, `solar_elevation`, `location`,
`location_id`.

## Installazione

### HACS (repository custom)

1. HACS → menu ⋮ → **Custom repositories**
2. URL di questo repository, categoria **Integration**
3. Installa **Meteo e Radar**, poi riavvia Home Assistant

### Manuale

Copia la cartella `custom_components/meteoeradar/` dentro `config/custom_components/`
della tua installazione e riavvia Home Assistant.

```
config/
└── custom_components/
    └── meteoeradar/
        ├── __init__.py
        ├── api.py
        ├── config_flow.py
        ├── const.py
        ├── coordinator.py
        ├── manifest.json
        ├── strings.json
        ├── symbols.py
        ├── weather.py
        └── translations/
            ├── en.json
            └── it.json
```

## Configurazione

**Impostazioni → Dispositivi e servizi → Aggiungi integrazione → "Meteo e Radar"**.

- Inserisci il nome di una località (es. `Cortina d'Ampezzo`), oppure
- lascia il campo vuoto per usare le coordinate configurate in Home Assistant
  (reverse geocoding automatico).

Puoi aggiungere più località ripetendo la procedura: ognuna crea un dispositivo
e un'entità `weather.*` distinti.

Da **Configura** si regola l'intervallo di aggiornamento (default 15 minuti,
minimo 5, massimo 120).

## Sensori

Oltre all'entità `weather.*`, l'integrazione crea sensori separati seguendo lo
schema delle integrazioni meteo ufficiali (AccuWeather, OpenWeatherMap,
Tomorrow.io): nomi tradotti, `device_class` e `state_class` corretti, e le
grandezze di nicchia disabilitate di default.

Gli entity_id sono espliciti e indipendenti dalla lingua:

```
sensor.meteoeradar_<località>_<grandezza>
```

per esempio `sensor.meteoeradar_milano_temperature`.

### Condizioni attuali

| Sensore | Unità | Note |
|---|---|---|
| `condition` | — | enum con le condizioni di Home Assistant |
| `temperature` | °C | |
| `apparent_temperature` | °C | |
| `humidity` | % | |
| `dew_point` | °C | |
| `pressure` | hPa | |
| `wind_speed` | km/h | |
| `wind_gust_speed` | km/h | |
| `wind_bearing` | ° | |
| `visibility` | km | dalla prima ora di previsione |
| `precipitation_probability` | % | |
| `cloud_cover` | % | disabilitato — vedi nota sotto |
| `precipitation_type` | — | disabilitato |
| `pressure_tendency` | — | disabilitato, diagnostico |
| `smog_level` | — | disabilitato, diagnostico |
| `solar_elevation` | ° | disabilitato, diagnostico |

`cloud_cover` non è una misura: il backend classifica il cielo in cinque livelli
e il sensore riporta il valore corrispondente (0 / 15 / 30 / 60 / 100 %).

### Previsione di oggi

| Sensore | Unità |
|---|---|
| `temperature_max` | °C |
| `temperature_min` | °C |
| `uv_index` | — |
| `precipitation_today` | mm |
| `sunshine_duration` | h |

### Qualità dell'aria

`air_quality_index` — indice europeo **1–6** (1 buona … 6 pessima), con
`description`, `color` e `source` come attributi. Creato solo dove il servizio
copre la località.

### Pollini

Un sensore per allergene, con valore **0–3** (0 assente, 3 alto) e attributi
`allergen`, `level`, `level_max`, `date`. Gli entity_id usano lo slug inglese:

```
sensor.meteoeradar_milano_birch
sensor.meteoeradar_milano_grasses
sensor.meteoeradar_milano_ragweed
```

I 25 allergeni possibili sono `alder`, `ash`, `beech`, `birch`, `chestnut`,
`cypress`, `elm`, `goosefoot`, `grasses`, `hazel`, `hornbeam`, `linden`,
`mugwort`, `nettle`, `oak`, `olive`, `pellitory`, `pine`, `plane`, `plantain`,
`poplar`, `ragweed`, `rumex`, `rye`, `willow`; vengono creati solo quelli che il
backend riporta per la località. La copertura è limitata ad alcuni paesi
europei — Italia, Germania, Austria, Svizzera, Francia, Spagna, Paesi Bassi,
Polonia fra quelli verificati. Altrove i sensori dei pollini non compaiono.

## Uso con clock-weather-card

```yaml
type: custom:clock-weather-card
entity: weather.roma_lazio_italia
sun_entity: sun.sun
temperature_sensor: sensor.meteoeradar_roma_temperature
humidity_sensor: sensor.meteoeradar_roma_humidity
apparent_sensor: sensor.meteoeradar_roma_apparent_temperature
locale: it
time_format: 24
forecast_rows: 5
hourly_forecast: false
show_humidity: true
animated_icon: true
```

La card legge le previsioni via `weather/subscribe_forecast`, quindi l'entità
`weather.*` da sola è sufficiente; i sensori servono solo se vuoi che i valori
mostrati vengano da lì.

### Nota su `aqi_sensor`

`clock-weather-card` colora l'AQI secondo la scala **statunitense EPA**
(soglie 50 / 100 / 150 / 200 / 300), mentre questa integrazione espone
l'indice **europeo 1–6**, che è il dato realmente fornito dal provider.
Passando `sensor.meteoeradar_<località>_air_quality_index` la card mostrerebbe
sempre il verde.

Se preferisci i colori della card a scapito della fedeltà del dato, crea un
sensore template che approssima le due scale — è una conversione arbitraria,
non una vera conversione di unità:

```yaml
template:
  - sensor:
      - name: AQI Roma (scala EPA approssimata)
        unique_id: meteoeradar_roma_aqi_epa
        state: >
          {% set eu = states('sensor.meteoeradar_roma_air_quality_index') | int(0) %}
          {{ {1: 25, 2: 75, 3: 125, 4: 175, 5: 250, 6: 350}.get(eu, 0) }}
```

## Uso con pollenprognos-card

[pollenprognos-card](https://github.com/krissen/pollenprognos-card) **non
funziona ancora** con questa integrazione. La card non ha una modalità
generica: riconosce gli 11 provider supportati da un pattern di entity_id
codificato in un adapter dedicato (`sensor.polleninformation_*`,
`sensor.pollenflug_*`, …), e l'opzione `entity_prefix` serve solo a indicare la
località, non a cambiare quel prefisso.

I sensori dei pollini di questa integrazione sono però modellati apposta sulla
stessa forma dell'adapter `peu` — `sensor.<integrazione>_<località>_<allergene>`
con slug inglesi e valore numerico — così che scrivere un adapter a monte sia
poco più di una copia. Nel frattempo i sensori restano usabili con le card
generiche (`entities`, `gauge`, `history-graph`) e nelle automazioni.

## Lingua

L'integrazione è tradotta in **italiano e inglese**: config flow, opzioni, nomi
dei sensori, nomi degli allergeni e stati della condizione seguono la lingua di
Home Assistant.

Gli entity_id **non** dipendono dalla lingua: restano
`sensor.meteoeradar_<località>_<grandezza>` in inglese, così le automazioni e le
card non si rompono cambiando lingua.

Una parte dei dati è tradotta lato server (il nome della località e la
descrizione della qualità dell'aria). Di default l'integrazione inoltra al
backend la lingua di Home Assistant; da **Configura → Lingua dei dati** puoi
forzare italiano o inglese. Il backend supporta una ventina di lingue e ripiega
sull'inglese per quelle che non conosce.

Il nome della località viene però risolto **una sola volta**, quando aggiungi
l'integrazione: cambiando lingua in seguito il dispositivo mantiene il nome
originale. Per rinominarlo, rimuovi e riaggiungi la località.

> La ricerca per nome è orientata dal paese configurato in Home Assistant.
> Con paese `GB`, cercare "Milano" restituisce Milano in Texas: usa il nome
> locale corretto ("Milan") oppure lascia il campo vuoto per usare le
> coordinate di Home Assistant.

## Mappatura dei simboli

Il backend restituisce codici di 6 caratteri (`so____`, `bds1__`, `mdsns3`…).
`symbols.py` li decodifica secondo la grammatica ricostruita dal bundle del
sito, che include anche una tabella `{regex, data}` con i valori semantici
`cloudy` / `rain` / `snow` / `freezing` / `lightning` / `sightDistance` usati per
lo sfondo dinamico: è da lì che deriva la mappatura.

Tutti i 166 codici del vocabolario ufficiale sono coperti — nessuno finisce su
`exceptional`:

| Condizione Home Assistant | Codici |
|---|---|
| `sunny` / `clear-night` | `so____` / `mo____` |
| `partlycloudy` | `ms`, `mm`, `wb`, `mb` (copertura 0.15–0.30) |
| `cloudy` | `bw`, `mw`, `bd`, `md` (copertura 0.60–1.00) |
| `fog` | `ns nb nn nm as ap an am cs ca cn cm` |
| `rainy` / `pouring` | suffissi `r1 r2 s1 s2` / `r3 s3` |
| `snowy` | suffissi `sn*`, `sns*`, `sg` |
| `snowy-rainy` | suffissi `sr*`, `srs*`, `gr*` (pioggia che gela) |
| `lightning-rainy` | suffissi `g1 g2 g3` |

## Aggiornamenti e rilasci

Ogni versione è pubblicata come **GitHub Release** con tag semver (`1.0.0`).
HACS legge le release e mostra il pulsante *Aggiorna* quando ne esce una nuova;
`hacs.json` dichiara `zip_release`, quindi HACS scarica l'asset `meteoeradar.zip`
allegato alla release invece del contenuto del branch.

Per pubblicare una nuova versione basta creare la release:

```bash
gh release create 1.0.1 --generate-notes
```

Il workflow [`release.yml`](.github/workflows/release.yml) si occupa del resto:

1. ricava la versione dal tag (accetta sia `1.0.1` sia `v1.0.1`) e rifiuta i tag
   non semver;
2. allinea `version` in `manifest.json` — così la versione mostrata da Home
   Assistant coincide sempre con quella della release;
3. crea `meteoeradar.zip` con i file dell'integrazione in radice;
4. lo allega alla release.

Il workflow [`validate.yml`](.github/workflows/validate.yml) esegue a ogni push
`hassfest`, la validazione HACS e il test di regressione sui codici simbolo.

Aggiornare l'installazione: HACS → **Meteo e Radar** → *Aggiorna*, poi riavvia
Home Assistant. In installazione manuale, sostituisci la cartella
`custom_components/meteoeradar/` con il contenuto dello zip della release.

## Limiti noti

- Le temperature arrivano già arrotondate all'intero dal backend.
- La quantità di precipitazione è fornita come intervallo (`interval_begin` /
  `interval_end`): viene usato il valore medio. Se il backend non prevede
  precipitazione il campo `details` è assente e il valore è `0.0`.
- `visibility` è presente solo nelle previsioni orarie, non nelle condizioni
  attuali.
- La ricerca per nome restituisce sempre la corrispondenza migliore (un solo
  risultato); il passo di disambiguazione è presente solo come fallback.

## Nota legale

Questa integrazione usa endpoint non documentati destinati alla web app di
meteoeradar.it. Non è affiliata né supportata da WetterOnline GmbH. I token di
accesso sono quelli pubblici incorporati nel sito e possono cambiare senza
preavviso, rompendo l'integrazione. Usala per scopi personali e mantieni un
intervallo di aggiornamento ragionevole.
