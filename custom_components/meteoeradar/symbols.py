"""Decodifica dei codici simbolo WetterOnline usati da meteoeradar.it.

Il backend restituisce per ogni intervallo un campo ``symbol`` di 6 caratteri
(riempito a destra con ``_``), ad esempio ``so____``, ``bds1__`` o ``mdsns3``.

La grammatica e' stata ricavata dal bundle del sito, che contiene sia l'elenco
completo dei 166 codici validi sia una tabella ``{regex, data}`` usata per lo
sfondo dinamico. Quella tabella associa a ogni famiglia di codici i valori
semantici ``cloudy`` / ``rain`` / ``snow`` / ``freezing`` / ``lightning`` /
``sightDistance``: e' da li' che deriva la mappatura verso le condizioni di
Home Assistant implementata qui sotto.

Struttura del codice::

    [ base (2 char) ][ fenomeno + intensita' (0-4 char) ]

Base (copertura nuvolosa e giorno/notte, da ``cloudy`` nella tabella del sito)::

    so / mo   0.00   sereno            (giorno / notte)
    ms / mm   0.15   poco nuvoloso
    wb / mb   0.30   parzialmente nuvoloso
    bw / mw   0.60   nuvoloso
    bd / md   1.00   coperto
    ns nb nn nm as ap an am cs ca cn cm   nebbia (sightDistance 50..500)

Suffisso (fenomeno)::

    <vuoto>        nessuna precipitazione
    r1 r2 r3       pioggia               intensita' 1..3
    s1 s2 s3       rovesci               intensita' 1..3
    sn1..3 sns1..3 neve / rovesci di neve
    sr1..3 srs1..3 neve mista a pioggia
    g1 g2 g3       temporale             (rain 0.5..1.0, lightning 1.0)
    sg             temporale di neve     (snow 1.0, lightning 0.5)
    gr1 gr2        pioggia che gela      (freezing 1.0)
"""

from __future__ import annotations

from typing import Final

# Basi che rappresentano una scena notturna (2a lettera "m"/"n" = Mond/Nacht).
NIGHT_BASES: Final[frozenset[str]] = frozenset(
    {"mo", "mm", "mb", "mw", "md", "nm", "am", "cm", "nn", "an", "cn"}
)

# Tutte le basi che il sito rende come nebbia (sightDistance 50 o 500 metri).
FOG_BASES: Final[frozenset[str]] = frozenset(
    {"ns", "nb", "nn", "nm", "as", "ap", "an", "am", "cs", "ca", "cn", "cm"}
)

# Copertura nuvolosa per base, valori presi dalla tabella del sito.
CLOUD_COVER: Final[dict[str, float]] = {
    "so": 0.0,
    "mo": 0.0,
    "ms": 0.15,
    "mm": 0.15,
    "wb": 0.30,
    "mb": 0.30,
    "bw": 0.60,
    "mw": 0.60,
    "bd": 1.00,
    "md": 1.00,
}

# Condizioni Home Assistant usate (sottoinsieme di homeassistant.components.weather).
CLEAR_DAY: Final = "sunny"
CLEAR_NIGHT: Final = "clear-night"
PARTLY_CLOUDY: Final = "partlycloudy"
CLOUDY: Final = "cloudy"
FOG: Final = "fog"
RAINY: Final = "rainy"
POURING: Final = "pouring"
SNOWY: Final = "snowy"
SNOWY_RAINY: Final = "snowy-rainy"
LIGHTNING_RAINY: Final = "lightning-rainy"
EXCEPTIONAL: Final = "exceptional"


# Tutte le condizioni che to_condition() puo' restituire: serve a dichiarare le
# `options` del sensore enum della condizione.
ALL_CONDITIONS: Final[tuple[str, ...]] = (
    CLEAR_DAY,
    CLEAR_NIGHT,
    PARTLY_CLOUDY,
    CLOUDY,
    FOG,
    RAINY,
    POURING,
    SNOWY,
    SNOWY_RAINY,
    LIGHTNING_RAINY,
    EXCEPTIONAL,
)


def _base(symbol: str | None) -> str:
    return (symbol or "").strip().lower()[:2]


def cloud_cover_percent(symbol: str | None) -> int | None:
    """Copertura nuvolosa in percentuale, dedotta dalla classe del simbolo.

    Non e' una misura: il backend classifica il cielo in cinque livelli
    (0 / 15 / 30 / 60 / 100 %) e questo restituisce il valore corrispondente.
    Per la nebbia e per i codici sconosciuti ritorna ``None``.
    """
    cover = CLOUD_COVER.get(_base(symbol))
    if cover is None:
        return None
    return int(round(cover * 100))


def _suffix(symbol: str | None) -> str:
    return (symbol or "").strip().lower()[2:].rstrip("_")


def is_night(symbol: str | None) -> bool:
    """True se il simbolo rappresenta una scena notturna."""
    return _base(symbol) in NIGHT_BASES


def _intensity(suffix: str) -> int:
    """Ultima cifra del suffisso (1 = debole, 3 = forte); 0 se assente."""
    for char in reversed(suffix):
        if char.isdigit():
            return int(char)
    return 0


def _sky_condition(base: str) -> str:
    """Condizione in assenza di precipitazioni."""
    if base in FOG_BASES:
        return FOG

    cover = CLOUD_COVER.get(base)
    if cover is None:
        return EXCEPTIONAL
    if cover == 0.0:
        return CLEAR_NIGHT if base in NIGHT_BASES else CLEAR_DAY
    if cover <= 0.30:
        return PARTLY_CLOUDY
    return CLOUDY


def to_condition(symbol: str | None) -> str:
    """Traduce un codice simbolo WetterOnline in una condizione Home Assistant.

    Ritorna ``exceptional`` per codici sconosciuti, cosi' che un eventuale
    ampliamento del vocabolario lato backend non faccia fallire l'entita'.
    """
    base = _base(symbol)
    suffix = _suffix(symbol)

    if suffix:
        # L'ordine dei controlli conta: "gr" e "sg" vanno prima delle famiglie
        # generiche "g" e "s".
        if suffix.startswith("gr"):
            return SNOWY_RAINY  # pioggia che gela
        if suffix.startswith("sg"):
            return SNOWY  # temporale di neve, HA non ha una condizione dedicata
        if suffix.startswith("g"):
            return LIGHTNING_RAINY
        if suffix.startswith("sn"):
            return SNOWY  # sn* e sns* (neve e rovesci di neve)
        if suffix.startswith("sr"):
            return SNOWY_RAINY  # sr* e srs* (neve mista a pioggia)
        if suffix[0] in ("r", "s"):
            return POURING if _intensity(suffix) >= 3 else RAINY

    return _sky_condition(base)
