"""Liczenie głosów ławy i agregacja propozycji SL/TP (kod, bez LLM)."""
from typing import Any, Dict

import numpy as np

from konfiguracja.ustawienia import TRYB
from lawa.sl_tp import statystyki_poziomow
from stan import AktualnyStan


def glosowanie(stan: AktualnyStan) -> Dict[str, Any]:
    print("----Głosowanie ławy----")
    opinie = stan.get("opinie") or {}
    if not opinie:
        raise RuntimeError("Brak opinii traderów — żaden trader nie oddał głosu.")

    za = {id_: o for id_, o in opinie.items() if o["glos"] == "TAK"}
    liczba_tak, liczba_nie = len(za), len(opinie) - len(za)
    decyzja = "TAK" if liczba_tak > liczba_nie else "NIE"
    print(f"TAK: {liczba_tak} | NIE: {liczba_nie} → {decyzja}")

    wynik = {
        "tak": liczba_tak,
        "nie": liczba_nie,
        "decyzja": decyzja,
        "glosy": {id_: o["glos"] for id_, o in opinie.items()},
    }
    if decyzja == "TAK":
        wynik["stop_loss"] = statystyki_poziomow([o["stop_loss"] for o in za.values()])
        wynik["take_profit"] = statystyki_poziomow([o["take_profit"] for o in za.values()])
        wynik["skala_pozycji_procent"] = float(np.median([o["wielkosc_pozycji_procent"] for o in za.values()]))
        return {"wynik_glosowania": wynik}

    return {
        "wynik_glosowania": wynik,
        "decyzja_koncowa": {
            "otworz_pozycje": False,
            "powody": [f"ława przeciw ({liczba_tak} TAK / {liczba_nie} NIE)"],
            "tryb": TRYB,
        },
    }


def po_glosowaniu(stan: AktualnyStan) -> str:
    """Warunkowa krawędź grafu: Head Trader tylko gdy TAK > NIE."""
    return "head_trader" if stan["wynik_glosowania"]["decyzja"] == "TAK" else "koniec"
