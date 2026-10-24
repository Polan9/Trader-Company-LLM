"""Twarde reguły SL/TP i wielkości pozycji — liczone w kodzie, nie przez LLM.

Wszystkie rachunki uwzględniają koszt transakcji (prowizje + poślizg + spread):
zysk netto = TP − cena − koszt, ryzyko netto = cena − SL + koszt."""
from typing import Any, Dict, List, Optional

import numpy as np

from konfiguracja.ustawienia import (
    MAKS_POZYCJA_PROCENT_BUDZETU,
    MAKS_SL_ATR,
    MIN_SL_ATR,
    MIN_ZYSK_DO_RYZYKA,
    POSLIZG_STRONA_PROCENT,
    PROWIZJA_STRONA_PROCENT,
    RYZYKO_NA_TRANSAKCJE_PROCENT,
    TOLERANCJA_ZYSK_DO_RYZYKA,
)


def koszt_transakcji_procent(spread_procent: Optional[float]) -> float:
    """Koszt wejścia + wyjścia w % wartości pozycji."""
    return 2 * (PROWIZJA_STRONA_PROCENT + POSLIZG_STRONA_PROCENT) + (spread_procent or 0.0)


def zysk_do_ryzyka_netto(cena: float, stop_loss: float, take_profit: float, koszt_procent: float) -> float:
    koszt = cena * koszt_procent / 100
    return (take_profit - cena - koszt) / (cena - stop_loss + koszt)


def minimalny_take_profit(cena: float, stop_loss: float, koszt_procent: float) -> float:
    """Najbliższy TP spełniający MIN_ZYSK_DO_RYZYKA po kosztach."""
    koszt = cena * koszt_procent / 100
    return cena + koszt + MIN_ZYSK_DO_RYZYKA * (cena - stop_loss + koszt)


def opis_regul(cena: float, atr: float, koszt_procent: float) -> str:
    """Reguły podawane w promptach — te same, które potem sprawdza kod."""
    sl_przyklad = cena - atr
    return f"""
    TWARDE REGUŁY (sprawdzane przez kod — złamanie = głos/decyzja nieważna):
    - Tylko long na spocie. Cena wejścia: {cena:.8g}.
    - Koszt wejścia + wyjścia (prowizje, poślizg, spread): {koszt_procent:.3f}% wartości pozycji
      (= {cena * koszt_procent / 100:.6g} na jednostkę).
    - Stop-loss poniżej ceny wejścia, w odległości {MIN_SL_ATR}–{MAKS_SL_ATR} × ATR
      (ATR = {atr:.6g}, czyli SL między {cena - MAKS_SL_ATR * atr:.8g} a {cena - MIN_SL_ATR * atr:.8g}).
    - Zysk/ryzyko PO KOSZTACH ≥ {MIN_ZYSK_DO_RYZYKA}:
      (TP − cena − koszt) / (cena − SL + koszt) ≥ {MIN_ZYSK_DO_RYZYKA}.
      Przykład: przy SL = {sl_przyklad:.8g} (1 × ATR) take-profit musi wynosić co najmniej
      {minimalny_take_profit(cena, sl_przyklad, koszt_procent):.8g}.
    """


def sprawdz_sl_tp(
    cena: float, stop_loss: Optional[float], take_profit: Optional[float], atr: float, koszt_procent: float
) -> List[str]:
    """Zwraca listę naruszeń reguł; pusta lista = poziomy poprawne."""
    if stop_loss is None or take_profit is None:
        return ["brak stop-loss lub take-profit"]
    bledy = []
    if not 0 < stop_loss < cena:
        bledy.append(f"stop-loss {stop_loss:.8g} nie jest poniżej ceny wejścia {cena:.8g}")
    if take_profit <= cena:
        bledy.append(f"take-profit {take_profit:.8g} nie jest powyżej ceny wejścia {cena:.8g}")
    if bledy:
        return bledy

    stosunek = zysk_do_ryzyka_netto(cena, stop_loss, take_profit, koszt_procent)
    if stosunek < MIN_ZYSK_DO_RYZYKA - TOLERANCJA_ZYSK_DO_RYZYKA:
        bledy.append(
            f"zysk/ryzyko po kosztach {stosunek:.2f} < {MIN_ZYSK_DO_RYZYKA} "
            f"(min. TP dla tego SL: {minimalny_take_profit(cena, stop_loss, koszt_procent):.8g})"
        )
    odleglosc_sl = cena - stop_loss
    if not MIN_SL_ATR * atr <= odleglosc_sl <= MAKS_SL_ATR * atr:
        bledy.append(f"odległość SL {odleglosc_sl / atr:.2f} × ATR poza zakresem {MIN_SL_ATR}–{MAKS_SL_ATR}")
    return bledy


def statystyki_poziomow(wartosci: List[float]) -> Dict[str, Any]:
    return {
        "mediana": float(np.median(wartosci)),
        "min": float(min(wartosci)),
        "max": float(max(wartosci)),
    }


def w_zakresie(wartosc: float, zakres: Dict[str, Any], tolerancja: float = 1e-9) -> bool:
    margines = abs(zakres["max"]) * tolerancja
    return zakres["min"] - margines <= wartosc <= zakres["max"] + margines


def oblicz_wielkosc_pozycji(
    budzet: float, cena: float, stop_loss: float, koszt_procent: float, skala_procent: float
) -> Dict[str, float]:
    """Wielkość pozycji tak, by trafienie SL (z kosztami) kosztowało RYZYKO_NA_TRANSAKCJE_PROCENT budżetu.
    Ograniczona limitem MAKS_POZYCJA_PROCENT_BUDZETU i przeskalowana przez ławę (skala ≤ 100%)."""
    strata_procent_przy_sl = (cena - stop_loss) / cena * 100 + koszt_procent
    ryzyko_usd = budzet * RYZYKO_NA_TRANSAKCJE_PROCENT / 100

    wielkosc_z_ryzyka = ryzyko_usd / (strata_procent_przy_sl / 100)
    limit = budzet * MAKS_POZYCJA_PROCENT_BUDZETU / 100
    wielkosc = min(wielkosc_z_ryzyka, limit) * min(max(skala_procent, 0.0), 100.0) / 100
    return {
        "wielkosc_usd": wielkosc,
        "ryzyko_usd": wielkosc * strata_procent_przy_sl / 100,
        "strata_procent_przy_sl": strata_procent_przy_sl,
        "koszt_procent": koszt_procent,
        "ograniczona_limitem": wielkosc_z_ryzyka > limit,
    }
