# Changelog

Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/)
e il versionamento è [semantico](https://semver.org/lang/it/).

## [1.1.0] — 2026-07-31

### Aggiunto
- Piattaforma `sensor`: 21 sensori separati per le grandezze meteo, modellati
  sulle integrazioni ufficiali (AccuWeather, OpenWeatherMap, Tomorrow.io) —
  `SensorEntityDescription` per grandezza, `device_class`/`state_class`
  corretti, grandezze di nicchia disabilitate di default.
- Sensore della qualità dell'aria (indice europeo 1–6) da `aqi/v1`.
- Sensori dei pollini da `pollen/v4`: uno per allergene, scala 0–3, fino a 25
  allergeni. Creati solo dove il servizio copre la località.
- Entity_id espliciti e indipendenti dalla lingua nella forma
  `sensor.meteoeradar_<località>_<grandezza>`.
- Opzione **Lingua dei dati** (automatica / italiano / inglese): la lingua
  inoltrata al backend, che determina il nome della località e la descrizione
  della qualità dell'aria.
- Traduzioni complete di sensori, allergeni e stati della condizione in
  italiano e inglese, verificate dal test di regressione.

### Modificato
- La lingua inviata alle API non è più fissa a `it`: segue Home Assistant.
- La regione usata per la ricerca geografica viene dal paese configurato in
  Home Assistant. Il parametro orienta i risultati — cercare "Milano" con
  regione `GB` restituisce una località in Texas.
- Le entry create con la 1.0.x acquisiscono al primo avvio il codice paese
  necessario ai pollini.

## [1.0.1] — 2026-07-31

### Aggiunto
- Asset di brand (icona e logo) sotto `custom_components/meteoeradar/brand/`,
  richiesti dalla validazione HACS.

## [1.0.0] — 2026-07-31

Prima release.

### Aggiunto
- Entità `weather.*` alimentata dalle API di meteoeradar.it (WetterOnline).
- Condizioni attuali e previsione oraria da `blending/shortcast/v1` (49 ore).
- Previsione giornaliera da `blending/forecast/v1` (14 giorni).
- Config flow da UI: ricerca per nome oppure reverse geocoding sulle coordinate
  di Home Assistant; più località configurabili in parallelo.
- Intervallo di aggiornamento configurabile (5–120 minuti, default 15).
- Decodifica completa dei 166 codici simbolo WetterOnline verso le condizioni
  di Home Assistant, con test di regressione.
- Traduzioni italiano e inglese.
