"""Statystyki stóp zwrotu i położenia ceny — blok danych dla statystyka (trader `statystyk`)."""
from typing import Any, Dict

import numpy as np
import pandas as pd

from konfiguracja.ustawienia import (
    OKNO_AUTOKORELACJI,
    OKNO_DLUGIE,
    OKNO_KROTKIE,
    OKNO_ZAKRESU,
    OKNO_ZSCORE,
)


def oblicz_statystyki(swiece: pd.DataFrame) -> Dict[str, Any]:
    zamkniecia = swiece["close"].astype(float)
    zwroty = zamkniecia.pct_change() * 100
    potrzebne = max(OKNO_DLUGIE, OKNO_AUTOKORELACJI, OKNO_ZAKRESU, OKNO_ZSCORE) + 1
    if len(zamkniecia) < potrzebne:
        raise RuntimeError(f"Za mało świec do statystyk ({len(zamkniecia)} < {potrzebne}).")

    cena = float(zamkniecia.iloc[-1])
    okno_z = zamkniecia.tail(OKNO_ZSCORE)
    odchylenie_z = float(okno_z.std(ddof=0))
    okno_zakresu = zamkniecia.tail(OKNO_ZAKRESU)
    minimum, maksimum = float(okno_zakresu.min()), float(okno_zakresu.max())

    return {
        "zwrot_ostatniej_swiecy": float(zwroty.iloc[-1]),
        "zwrot_okno_krotkie": float((cena / zamkniecia.iloc[-1 - OKNO_KROTKIE] - 1) * 100),
        "zmiennosc_okno_krotkie": float(zwroty.tail(OKNO_KROTKIE).std()),
        "zmiennosc_okno_dlugie": float(zwroty.tail(OKNO_DLUGIE).std()),
        "zscore_ceny": (cena - float(okno_z.mean())) / odchylenie_z if odchylenie_z else 0.0,
        "pozycja_w_zakresie": (cena - minimum) / (maksimum - minimum) * 100 if maksimum > minimum else 50.0,
        "autokorelacja_lag1": float(zwroty.tail(OKNO_AUTOKORELACJI).autocorr(lag=1)),
        "udzial_swiec_wzrostowych": float((zwroty.tail(OKNO_KROTKIE) > 0).mean() * 100),
    }


def formatuj_statystyki(statystyki: Dict[str, Any]) -> str:
    s = statystyki
    autokorelacja = s["autokorelacja_lag1"]
    if np.isnan(autokorelacja):
        opis_autokorelacji = "brak danych"
    elif autokorelacja > 0.1:
        opis_autokorelacji = "dodatnia — ruchy mają tendencję do kontynuacji"
    elif autokorelacja < -0.1:
        opis_autokorelacji = "ujemna — ruchy mają tendencję do odwracania się"
    else:
        opis_autokorelacji = "bliska zera — brak wyraźnej zależności"
    return f"""
    STATYSTYKI (zwroty w % na świecę):
    - Zwrot ostatniej świecy: {s['zwrot_ostatniej_swiecy']:+.3f}%
    - Zwrot z ostatnich {OKNO_KROTKIE} świec: {s['zwrot_okno_krotkie']:+.3f}%
    - Świece wzrostowe w ostatnich {OKNO_KROTKIE}: {s['udzial_swiec_wzrostowych']:.0f}%
    - Zmienność (odch. std. zwrotów): {OKNO_KROTKIE} świec {s['zmiennosc_okno_krotkie']:.3f}% | {OKNO_DLUGIE} świec {s['zmiennosc_okno_dlugie']:.3f}%
    - Z-score ceny względem średniej {OKNO_ZSCORE} świec: {s['zscore_ceny']:+.2f}
    - Pozycja ceny w zakresie {OKNO_ZAKRESU} świec (0 = minimum, 100 = maksimum): {s['pozycja_w_zakresie']:.0f}
    - Autokorelacja zwrotów (lag 1, {OKNO_AUTOKORELACJI} świec): {autokorelacja:+.3f} — {opis_autokorelacji}
    """
