"""Zapis stanu rundy do pliku tekstowego — tymczasowo, docelowo baza danych."""
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from konfiguracja.ustawienia import PLIK_STANU, SWIECE_W_PROMPCIE
from stan import AktualnyStan
from wskazniki.analiza_techniczna import formatuj_analize_techniczna
from wskazniki.statystyki import formatuj_statystyki


def _slownik(dane: Dict[str, Any]) -> List[str]:
    return [f"{klucz}: {wartosc}" for klucz, wartosc in dane.items()] if dane else ["(brak)"]


def _opinie(opinie: Dict[str, Dict[str, Any]]) -> List[str]:
    if not opinie:
        return ["(brak)"]
    linie = []
    for id_, opinia in opinie.items():
        linie.append(f"[{id_}] {opinia['nazwa']} ({opinia['model']}): {opinia['glos']}")
        if opinia["glos"] == "TAK":
            linie.append(
                f"  SL: {opinia['stop_loss']} | TP: {opinia['take_profit']} | pozycja: {opinia['wielkosc_pozycji_procent']}%"
            )
        linie.append(f"  Uzasadnienie: {opinia['uzasadnienie'] or '(brak)'}")
        linie.extend(f"  Uwaga: {uwaga}" for uwaga in opinia["uwagi"])
    return linie


def zapisz_stan(stan: AktualnyStan, nazwa_pliku: Path = PLIK_STANU):
    linie = [
        "=== STAN TRADINGU ===",
        f"symbol: {stan['symbol']}",
        f"interwal: {stan['interwal']}",
        f"budzet: {stan['budzet']}",
        "",
        "=== DECYZJA KOŃCOWA ===",
        *_slownik(stan.get("decyzja_koncowa")),
        "",
        "=== WYNIK GŁOSOWANIA ===",
        *_slownik(stan.get("wynik_glosowania")),
        "",
        "=== OPINIE TRADERÓW ===",
        *_opinie(stan.get("opinie")),
        "",
        "=== DECYZJA HEAD TRADERA ===",
        *_slownik(stan.get("decyzja_head_tradera")),
        "",
        "=== AKTUALNE DANE (TICKER) ===",
        *_slownik(stan.get("aktualne_dane")),
        "",
        "=== ANALIZA TECHNICZNA ===",
    ]
    analiza = stan.get("analiza_techniczna") or {}
    if analiza:
        linie.append(formatuj_analize_techniczna(analiza).strip())
        linie.append(formatuj_statystyki(analiza["statystyki"]).strip())
    else:
        linie.append("(brak)")

    linie.extend(["", f"=== HISTORIA SWIEC (ostatnie {SWIECE_W_PROMPCIE}) ==="])
    swiece = stan.get("dane_historyczne")
    if isinstance(swiece, pd.DataFrame) and not swiece.empty:
        linie.append(swiece.tail(SWIECE_W_PROMPCIE).to_string(index=False))
    else:
        linie.append("(brak)")

    with open(nazwa_pliku, "w", encoding="utf-8") as plik:
        plik.write("\n".join(linie))
    print(f"Zapisano stan do pliku: {nazwa_pliku}")
