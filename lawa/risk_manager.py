"""Risk Manager — twarde limity w kodzie i prawo weta; wylicza wielkość pozycji."""
from typing import Any, Dict

from dane.gielda import cena_wejscia
from konfiguracja.ustawienia import (
    MAKS_DZIENNA_STRATA_PROCENT,
    MAKS_TRANSAKCJI_DZIENNIE,
    MIN_WIELKOSC_POZYCJI_USD,
    TRYB,
)
from lawa.sl_tp import koszt_transakcji_procent, oblicz_wielkosc_pozycji, sprawdz_sl_tp, zysk_do_ryzyka_netto
from stan import AktualnyStan


def risk_manager(stan: AktualnyStan) -> Dict[str, Any]:
    print("----Risk Manager----")
    decyzja = stan["decyzja_head_tradera"]
    cena = cena_wejscia(stan["aktualne_dane"])
    atr = stan["analiza_techniczna"]["atr"]["wartosc"]
    koszt = koszt_transakcji_procent(stan["aktualne_dane"].get("spread_procent"))
    stop_loss, take_profit = decyzja["stop_loss"], decyzja["take_profit"]

    weto = sprawdz_sl_tp(cena, stop_loss, take_profit, atr, koszt)
    if stan.get("dzienna_strata_procent", 0.0) >= MAKS_DZIENNA_STRATA_PROCENT:
        weto.append(f"osiągnięty limit dziennej straty ({MAKS_DZIENNA_STRATA_PROCENT}%)")
    if stan.get("transakcje_dzisiaj", 0) >= MAKS_TRANSAKCJI_DZIENNIE:
        weto.append(f"osiągnięty limit transakcji dziennie ({MAKS_TRANSAKCJI_DZIENNIE})")

    pozycja = {}
    if not weto:
        pozycja = oblicz_wielkosc_pozycji(
            stan["budzet"], cena, stop_loss, koszt, stan["wynik_glosowania"]["skala_pozycji_procent"]
        )
        pozycja["zysk_do_ryzyka_netto"] = zysk_do_ryzyka_netto(cena, stop_loss, take_profit, koszt)
        if pozycja["wielkosc_usd"] < MIN_WIELKOSC_POZYCJI_USD:
            weto.append(f"pozycja {pozycja['wielkosc_usd']:.2f} USD poniżej minimum {MIN_WIELKOSC_POZYCJI_USD} USD")

    if weto:
        print("WETO: " + "; ".join(weto))
    return {
        "decyzja_koncowa": {
            "otworz_pozycje": not weto,
            "powody": ["weto Risk Managera: " + "; ".join(weto)] if weto else ["ława za, Risk Manager zatwierdził"],
            "tryb": TRYB,
            "cena_wejscia": cena,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "zrodlo_poziomow": decyzja["zrodlo"],
            **pozycja,
        }
    }
