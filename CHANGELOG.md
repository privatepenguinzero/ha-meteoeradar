# Changelog

Il formato segue [Keep a Changelog](https://keepachangelog.com/it/1.1.0/)
e il versionamento è [semantico](https://semver.org/lang/it/).

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
