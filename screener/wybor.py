"""Screener: przed zwołaniem ławy wybiera parę, na której ruch najlepiej pokrywa koszty.

Kryteria twarde (z analizy analizy/atr_vs_koszty.py): aktywna para spot */USDT spoza listy
wykluczonych, minimalny wolumen, maksymalny spread, ATR% powyżej progu „stablecoina”
i koszt transakcji < SCREENER_MAKS_KOSZT_DO_ATR % ATR. Ranking: najniższy koszt/ATR."""
from typing import Any, Dict, List, Optional, Set

import ccxt
import pandas as pd

from dane.gielda import tylko_zamkniete_swiece
from konfiguracja.ustawienia import (
    SCREENER_LICZBA_KANDYDATOW,
    SCREENER_MAKS_KOSZT_DO_ATR,
    SCREENER_MAKS_SPREAD_PROCENT,
    SCREENER_MIN_ATR_PROCENT,
    SCREENER_MIN_WOLUMEN_USDT,
    SCREENER_OKNO_ATR,
    SCREENER_SWIECE,
    WYKLUCZONE_AKTYWA,
)
from lawa.sl_tp import koszt_transakcji_procent
from wskazniki.obliczenia import atr


def _kandydaci(gielda: ccxt.Exchange, pomin: Set[str]) -> List[Dict[str, Any]]:
    """Najpłynniejsze pary spełniające filtry z tickera (bez pobierania świec)."""
    rynki = gielda.load_markets()
    kandydaci = []
    for symbol, ticker in gielda.fetch_tickers().items():
        rynek = rynki.get(symbol)
        if not rynek or not rynek.get("spot") or not rynek.get("active") or rynek["quote"] != "USDT":
            continue
        if rynek["base"] in WYKLUCZONE_AKTYWA or symbol in pomin:
            continue
        bid, ask = ticker.get("bid"), ticker.get("ask")
        if not bid or not ask:
            continue
        kandydaci.append({
            "symbol": symbol,
            "wolumen_usdt_24h": float(ticker.get("quoteVolume") or 0),
            "spread_procent": (ask - bid) / ((ask + bid) / 2) * 100,
        })
    kandydaci.sort(key=lambda k: k["wolumen_usdt_24h"], reverse=True)
    return kandydaci[:SCREENER_LICZBA_KANDYDATOW]


def _mediana_atr_procent(gielda: ccxt.Exchange, symbol: str, interwal: str) -> Optional[float]:
    surowe = gielda.fetch_ohlcv(symbol, interwal, limit=SCREENER_SWIECE + 1)
    surowe = tylko_zamkniete_swiece(surowe, interwal, gielda.milliseconds())
    swiece = pd.DataFrame(surowe, columns=["timestamp", "open", "high", "low", "close", "volume"])
    atr_procent = (atr(swiece) / swiece["close"] * 100).dropna()
    if len(atr_procent) < SCREENER_OKNO_ATR:
        return None
    return float(atr_procent.tail(SCREENER_OKNO_ATR).median())


def ocen_pare(kandydat: Dict[str, Any], atr_procent: Optional[float]) -> Dict[str, Any]:
    """Dopisuje koszt, koszt/ATR i listę odrzuceń do kandydata (pusta lista = para przechodzi)."""
    koszt = koszt_transakcji_procent(kandydat["spread_procent"])
    odrzucenia = []
    if kandydat["wolumen_usdt_24h"] < SCREENER_MIN_WOLUMEN_USDT:
        odrzucenia.append("wolumen")
    if kandydat["spread_procent"] > SCREENER_MAKS_SPREAD_PROCENT:
        odrzucenia.append("spread")
    if atr_procent is None:
        odrzucenia.append("za mało świec")
        koszt_do_atr = None
    else:
        koszt_do_atr = koszt / atr_procent * 100
        if atr_procent < SCREENER_MIN_ATR_PROCENT:
            odrzucenia.append("ATR jak stablecoin")
        elif koszt_do_atr > SCREENER_MAKS_KOSZT_DO_ATR:
            odrzucenia.append("koszt/ATR")
    return {**kandydat, "atr_procent": atr_procent, "koszt_procent": koszt,
            "koszt_do_atr": koszt_do_atr, "odrzucenia": odrzucenia}


def wybierz_pare(interwal: str, pomin: Set[str] = frozenset()) -> Dict[str, Any]:
    """Ranking kandydatów i wybór pary dla ławy.

    `pomin` — pary wykluczone w tej rundzie (np. z otwartą pozycją).
    Zwraca: {"symbol": wybrana para albo None, "ranking": [...], "odrzucone": liczba}."""
    gielda = ccxt.binance({"enableRateLimit": True})
    ocenione = []
    for kandydat in _kandydaci(gielda, set(pomin)):
        try:
            atr_procent = _mediana_atr_procent(gielda, kandydat["symbol"], interwal)
        except Exception:
            atr_procent = None  # pojedyncza para z błędem nie zatrzymuje screenera
        ocenione.append(ocen_pare(kandydat, atr_procent))

    przechodzi = sorted(
        (o for o in ocenione if not o["odrzucenia"]),
        key=lambda o: (o["koszt_do_atr"], -o["wolumen_usdt_24h"]),
    )
    return {
        "symbol": przechodzi[0]["symbol"] if przechodzi else None,
        "ranking": przechodzi,
        "odrzucone": [o for o in ocenione if o["odrzucenia"]],
    }


def formatuj_ranking(wynik: Dict[str, Any], liczba: int = 10) -> str:
    linie = [f"Screener: wybrano {wynik['symbol'] or 'BRAK'} "
             f"({len(wynik['ranking'])} par spełnia kryteria, {len(wynik['odrzucone'])} odrzuconych)"]
    for miejsce, para in enumerate(wynik["ranking"][:liczba], start=1):
        linie.append(
            f"  {miejsce:>2}. {para['symbol']:<12} koszt/ATR {para['koszt_do_atr']:5.1f}% | ATR {para['atr_procent']:.3f}% "
            f"| spread {para['spread_procent']:.4f}% | wolumen {para['wolumen_usdt_24h'] / 1e6:,.0f} mln USDT"
        )
    return "\n".join(linie)
