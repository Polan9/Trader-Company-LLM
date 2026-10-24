"""Czyste funkcje liczące wskaźniki — definicje zgodne z TradingView."""
import numpy as np
import pandas as pd

from konfiguracja.ustawienia import MACD_SYGNAL, MACD_SZYBKI, MACD_WOLNY, OKRES_ATR, OKRES_RSI


def _wygladz(seria: pd.Series, okres: int, alpha: float) -> pd.Series:
    """Wygładzanie wykładnicze ze startem od SMA z pierwszych `okres` wartości
    (tak liczą TradingView i większość platform). Wiodące NaN są pomijane."""
    wartosci = seria.to_numpy(dtype=float)
    wynik = np.full(len(wartosci), np.nan)
    poprawne = np.flatnonzero(~np.isnan(wartosci))
    if len(poprawne) < okres:
        return pd.Series(wynik, index=seria.index)

    koniec_startu = poprawne[0] + okres - 1
    wynik[koniec_startu] = wartosci[poprawne[0]:koniec_startu + 1].mean()
    for i in range(koniec_startu + 1, len(wartosci)):
        wynik[i] = alpha * wartosci[i] + (1 - alpha) * wynik[i - 1]
    return pd.Series(wynik, index=seria.index)


def ema(seria: pd.Series, okres: int) -> pd.Series:
    return _wygladz(seria, okres, alpha=2 / (okres + 1))


def rma(seria: pd.Series, okres: int) -> pd.Series:
    """Średnia Wildera — używana w klasycznym RSI i ATR."""
    return _wygladz(seria, okres, alpha=1 / okres)


def rsi(zamkniecia: pd.Series, okres: int = OKRES_RSI) -> pd.Series:
    delta = zamkniecia.diff()
    sredni_zysk = rma(delta.clip(lower=0), okres)
    srednia_strata = rma(-delta.clip(upper=0), okres)
    wynik = 100 - 100 / (1 + sredni_zysk / srednia_strata)
    wynik = wynik.where(srednia_strata != 0, 100.0)  # same wzrosty
    wynik = wynik.where(~((sredni_zysk == 0) & (srednia_strata == 0)), 50.0)  # brak ruchu
    return wynik


def macd(zamkniecia: pd.Series, szybki: int = MACD_SZYBKI, wolny: int = MACD_WOLNY, sygnal: int = MACD_SYGNAL):
    linia = ema(zamkniecia, szybki) - ema(zamkniecia, wolny)
    linia_sygnalu = ema(linia, sygnal)
    histogram = linia - linia_sygnalu
    return linia, linia_sygnalu, histogram


def true_range(swiece: pd.DataFrame) -> pd.Series:
    """Największa z: high-low, |high-poprz. close|, |low-poprz. close|.
    Dla pierwszej świecy (brak poprzedniego zamknięcia) — high-low."""
    high = swiece["high"].astype(float)
    low = swiece["low"].astype(float)
    poprzednie_zamkniecie = swiece["close"].astype(float).shift(1)
    zakresy = pd.concat(
        [high - low, (high - poprzednie_zamkniecie).abs(), (low - poprzednie_zamkniecie).abs()],
        axis=1,
    )
    return zakresy.max(axis=1, skipna=True)


def atr(swiece: pd.DataFrame, okres: int = OKRES_ATR) -> pd.Series:
    """Average True Range z wygładzaniem Wildera."""
    return rma(true_range(swiece), okres)


def nachylenie_procentowe(seria: pd.Series) -> float:
    """Nachylenie prostej dopasowanej do serii, w % średniej na jedną świecę."""
    srednia = float(seria.mean())
    if srednia == 0:
        return 0.0
    nachylenie = np.polyfit(np.arange(len(seria)), seria.to_numpy(dtype=float), 1)[0]
    return float(nachylenie / srednia * 100)
