"""Zapis stanu rundy do pliku tekstowego — tymczasowo, docelowo baza danych."""
from pathlib import Path

import pandas as pd

from konfiguracja.ustawienia import PLIK_STANU, SWIECE_W_PROMPCIE
from stan import AktualnyStan
from wskazniki.analiza_techniczna import formatuj_analize_techniczna


def zapisz_stan(stan: AktualnyStan, nazwa_pliku: Path = PLIK_STANU):
    linie = [
        "=== STAN TRADINGU ===",
        f"symbol: {stan['symbol']}",
        f"interwal: {stan['interwal']}",
        f"budzet: {stan['budzet']}",
        "",
        "=== AKTUALNE DANE (TICKER) ===",
    ]
    for klucz, wartosc in stan.get("aktualne_dane", {}).items():
        linie.append(f"{klucz}: {wartosc}")

    linie.extend(["", "=== ANALIZA TECHNICZNA ==="])
    analiza = stan.get("analiza_techniczna") or {}
    if analiza:
        linie.append(formatuj_analize_techniczna(analiza).strip())
    else:
        linie.append("(brak)")

    linie.extend([
        "",
        "=== DECYZJA ANALITYKA ===",
        stan.get("decyzja_analityka") or "(brak)",
        "",
        "=== DECYZJA HEAD TRADERA ===",
        stan.get("decyzja_head_tradera") or "(brak)",
        "",
        f"=== HISTORIA SWIEC (ostatnie {SWIECE_W_PROMPCIE}) ===",
    ])
    swiece = stan.get("dane_historyczne")
    if isinstance(swiece, pd.DataFrame) and not swiece.empty:
        linie.append(swiece.tail(SWIECE_W_PROMPCIE).to_string(index=False))
    else:
        linie.append("(brak)")

    with open(nazwa_pliku, "w", encoding="utf-8") as plik:
        plik.write("\n".join(linie))
    print(f"Zapisano stan do pliku: {nazwa_pliku}")
