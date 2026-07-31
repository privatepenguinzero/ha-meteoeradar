"""Verifica la decodifica dei codici simbolo WetterOnline.

Eseguibile senza Home Assistant: ``python tests/test_symbols.py``.
L'elenco dei codici e' il vocabolario completo estratto dal bundle del sito
(``Y.symbols`` in ``main.<hash>.js``); se il backend ne introduce di nuovi il
test fallisce segnalando quali finiscono su ``exceptional``.
"""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "meteoeradar"))

import symbols  # noqa: E402

# I 166 codici validi dichiarati dal bundle di meteoeradar.it.
ALL_SYMBOLS = [
    "am____", "an____", "ap____", "as____", "bd____", "bdg1__",
    "bdg2__", "bdg3__", "bdgr1_", "bdgr2_", "bdr1__", "bdr2__",
    "bdr3__", "bds1__", "bds2__", "bds3__", "bdsg__", "bdsn1_",
    "bdsn2_", "bdsn3_", "bdsns1", "bdsns2", "bdsns3", "bdsr1_",
    "bdsr2_", "bdsr3_", "bdsrs1", "bdsrs2", "bdsrs3", "bw____",
    "bwg1__", "bwg2__", "bwg3__", "bwgr1_", "bwgr2_", "bwr1__",
    "bwr2__", "bwr3__", "bws1__", "bws2__", "bws3__", "bwsg__",
    "bwsn1_", "bwsn2_", "bwsn3_", "bwsns1", "bwsns2", "bwsns3",
    "bwsr1_", "bwsr2_", "bwsr3_", "bwsrs1", "bwsrs2", "bwsrs3",
    "ca____", "cm____", "cn____", "cs____", "mb____", "mbg1__",
    "mbg2__", "mbg3__", "mbgr1_", "mbgr2_", "mbr1__", "mbr2__",
    "mbr3__", "mbs1__", "mbs2__", "mbs3__", "mbsg__", "mbsn1_",
    "mbsn2_", "mbsn3_", "mbsns1", "mbsns2", "mbsns3", "mbsr1_",
    "mbsr2_", "mbsr3_", "mbsrs1", "mbsrs2", "mbsrs3", "md____",
    "mdg1__", "mdg2__", "mdg3__", "mdgr1_", "mdgr2_", "mdr1__",
    "mdr2__", "mdr3__", "mds1__", "mds2__", "mds3__", "mdsg__",
    "mdsn1_", "mdsn2_", "mdsn3_", "mdsns1", "mdsns2", "mdsns3",
    "mdsr1_", "mdsr2_", "mdsr3_", "mdsrs1", "mdsrs2", "mdsrs3",
    "mm____", "mo____", "ms____", "mw____", "mwg1__", "mwg2__",
    "mwg3__", "mwgr1_", "mwgr2_", "mwr1__", "mwr2__", "mwr3__",
    "mws1__", "mws2__", "mws3__", "mwsg__", "mwsn1_", "mwsn2_",
    "mwsn3_", "mwsns1", "mwsns2", "mwsns3", "mwsr1_", "mwsr2_",
    "mwsr3_", "mwsrs1", "mwsrs2", "mwsrs3", "nb____", "nm____",
    "nn____", "ns____", "so____", "wb____", "wbg1__", "wbg2__",
    "wbg3__", "wbgr1_", "wbgr2_", "wbr1__", "wbr2__", "wbr3__",
    "wbs1__", "wbs2__", "wbs3__", "wbsg__", "wbsn1_", "wbsn2_",
    "wbsn3_", "wbsns1", "wbsns2", "wbsns3", "wbsr1_", "wbsr2_",
    "wbsr3_", "wbsrs1", "wbsrs2", "wbsrs3",
]

# Casi rappresentativi di ogni famiglia.
EXPECTED = {
    "so____": "sunny",
    "mo____": "clear-night",
    "ms____": "partlycloudy",
    "mm____": "partlycloudy",
    "wb____": "partlycloudy",
    "mb____": "partlycloudy",
    "bw____": "cloudy",
    "bd____": "cloudy",
    "md____": "cloudy",
    "ns____": "fog",
    "nm____": "fog",
    "cn____": "fog",
    "bdr1__": "rainy",
    "bds2__": "rainy",
    "bdr3__": "pouring",
    "bds3__": "pouring",
    "bdsn1_": "snowy",
    "mdsns3": "snowy",
    "bdsg__": "snowy",
    "bdsr1_": "snowy-rainy",
    "bdsrs3": "snowy-rainy",
    "bdgr1_": "snowy-rainy",
    "bdg1__": "lightning-rainy",
    "mwg3__": "lightning-rainy",
}

NIGHT = ["mo____", "mm____", "mb____", "mw____", "md____", "mdsn1_", "nm____", "cn____"]
DAY = ["so____", "ms____", "wb____", "bw____", "bd____", "bds1__", "ns____", "cs____"]


def main() -> int:
    failures: list[str] = []

    unknown = [c for c in ALL_SYMBOLS if symbols.to_condition(c) == "exceptional"]
    if unknown:
        failures.append(f"codici non riconosciuti: {unknown}")

    for code, expected in EXPECTED.items():
        actual = symbols.to_condition(code)
        if actual != expected:
            failures.append(f"{code}: atteso {expected}, ottenuto {actual}")

    for code in NIGHT:
        if not symbols.is_night(code):
            failures.append(f"{code} doveva essere notturno")
    for code in DAY:
        if symbols.is_night(code):
            failures.append(f"{code} non doveva essere notturno")

    night_count = sum(1 for c in ALL_SYMBOLS if symbols.is_night(c))
    if night_count != len(ALL_SYMBOLS) // 2:
        failures.append(
            f"attese {len(ALL_SYMBOLS) // 2} varianti notturne, trovate {night_count}"
        )

    if failures:
        print("FALLITO:")
        for line in failures:
            print("  -", line)
        return 1

    print(f"OK: {len(ALL_SYMBOLS)} codici, nessuno su 'exceptional', {night_count} notturni")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
