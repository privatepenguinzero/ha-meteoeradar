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

## Uso con clock-weather-card

```yaml
type: custom:clock-weather-card
entity: weather.roma_lazio_italia
locale: it
time_format: 24
forecast_rows: 5
hourly_forecast: false
show_humidity: true
animated_icon: true
```

Versione con previsione oraria:

```yaml
type: custom:clock-weather-card
entity: weather.roma_lazio_italia
locale: it
hourly_forecast: true
forecast_rows: 8
```

La card legge le previsioni via `weather/subscribe_forecast`, quindi non serve
nessuna configurazione aggiuntiva lato card.

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
