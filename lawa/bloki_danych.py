"""Rejestr bloków danych, z których składane są prompty traderów.

Nazwa bloku w `zakres_danych` konfiguracji tradera → funkcja `(stan) -> str`.
Nowy blok = nowa pozycja w BLOKI_DANYCH; konfiguracja ról się nie zmienia."""
from typing import Callable, Dict, List

from dane.gielda import formatuj_swiece, formatuj_ticker
from konfiguracja.ustawienia import SWIECE_KROTKIE_W_PROMPCIE
from stan import AktualnyStan
from wskazniki.analiza_techniczna import (
    formatuj_atr,
    formatuj_macd,
    formatuj_rsi,
    formatuj_sygnaly_heurystyczne,
    formatuj_wolumen,
)
from wskazniki.statystyki import formatuj_statystyki


def _blok_newsy(stan: AktualnyStan) -> str:
    return """
    NEWSY I SENTYMENT:
    - (moduł newsów jeszcze niedostępny — brak danych)
    """


BLOKI_DANYCH: Dict[str, Callable[[AktualnyStan], str]] = {
    "ticker": lambda stan: formatuj_ticker(stan["aktualne_dane"]),
    "swiece": lambda stan: formatuj_swiece(stan["dane_historyczne"], stan["interwal"]),
    "swiece_krotkie": lambda stan: formatuj_swiece(
        stan["dane_historyczne"], stan["interwal"], SWIECE_KROTKIE_W_PROMPCIE
    ),
    "wolumen": lambda stan: formatuj_wolumen(stan["analiza_techniczna"]),
    "rsi": lambda stan: formatuj_rsi(stan["analiza_techniczna"]),
    "macd": lambda stan: formatuj_macd(stan["analiza_techniczna"]),
    "atr": lambda stan: formatuj_atr(stan["analiza_techniczna"]),
    "sygnaly_heurystyczne": lambda stan: formatuj_sygnaly_heurystyczne(stan["analiza_techniczna"]),
    "statystyki": lambda stan: formatuj_statystyki(stan["analiza_techniczna"]["statystyki"]),
    "newsy": _blok_newsy,
}


def sprawdz_zakres_danych(zakres_danych: List[str], kto: str) -> None:
    nieznane = [blok for blok in zakres_danych if blok not in BLOKI_DANYCH]
    if nieznane:
        raise ValueError(
            f"{kto}: nieznane bloki danych {nieznane}. Dostępne: {sorted(BLOKI_DANYCH)}"
        )


def zloz_dane(stan: AktualnyStan, zakres_danych: List[str]) -> str:
    return "\n".join(BLOKI_DANYCH[blok](stan) for blok in zakres_danych)
