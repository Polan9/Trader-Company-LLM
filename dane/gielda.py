from typing import Any, Dict

import ccxt
import pandas as pd

from konfiguracja.ustawienia import LIMIT_SWIEC, SWIECE_W_PROMPCIE
from stan import AktualnyStan


def _tylko_zamkniete_swiece(surowe_swiece: list, interwal: str, teraz_ms: int) -> list:
    """Odrzuca świecę, która jeszcze trwa — giełda zwraca ją jako ostatnią."""
    dlugosc_ms = ccxt.Exchange.parse_timeframe(interwal) * 1000
    return [swieca for swieca in surowe_swiece if swieca[0] + dlugosc_ms <= teraz_ms]


def pobierz_dane(stan: AktualnyStan):
    try:
        gielda = ccxt.binance({"enableRateLimit": True})

        ticker = gielda.fetch_ticker(stan["symbol"])
        znacznik_czasu = ticker.get("timestamp")
        bid, ask = ticker.get("bid"), ticker.get("ask")
        spread_procent = (
            (ask - bid) / ((ask + bid) / 2) * 100 if bid and ask else None
        )
        # Pola 24h z tickera spot; markPrice/indexPrice pominięte — istnieją tylko na futures.
        aktualne_dane = {
            "last": ticker.get("last"),
            "open": ticker.get("open"),
            "high": ticker.get("high"),
            "low": ticker.get("low"),
            "vwap": ticker.get("vwap"),
            "average": ticker.get("average"),
            "change": ticker.get("change"),
            "percentage": ticker.get("percentage"),
            "baseVolume": ticker.get("baseVolume"),
            "quoteVolume": ticker.get("quoteVolume"),
            "bid": bid,
            "bidVolume": ticker.get("bidVolume"),
            "ask": ask,
            "askVolume": ticker.get("askVolume"),
            "spread_procent": spread_procent,
            "timestamp": pd.to_datetime(znacznik_czasu, unit="ms", utc=True) if znacznik_czasu else None,
        }

        # +1, bo ostatnia (niezamknięta) świeca zostanie odrzucona
        surowe_swiece = gielda.fetch_ohlcv(stan["symbol"], stan["interwal"], limit=LIMIT_SWIEC + 1)
        teraz_ms = znacznik_czasu or gielda.milliseconds()
        surowe_swiece = _tylko_zamkniete_swiece(surowe_swiece, stan["interwal"], teraz_ms)

        swiece = pd.DataFrame(surowe_swiece, columns=["timestamp", "open", "high", "low", "close", "volume"])
        swiece["timestamp"] = pd.to_datetime(swiece["timestamp"], unit="ms", utc=True)

        return {
            "aktualne_dane": aktualne_dane,
            "dane_historyczne": swiece,
        }
    except Exception as blad:
        print(f"Błąd pobierania danych: {blad}")
        raise


def _format_procent(wartosc) -> str:
    return f"{wartosc:.4f}%" if wartosc is not None else "brak"


def formatuj_ticker(aktualne_dane: Dict[str, Any]) -> str:
    return f"""
    --- AKTUALNE DANE RYNKOWE (TICKER, okno 24h) ---
    - Ostatnia cena (last): {aktualne_dane['last']} USDT
    - Otwarcie 24h (open): {aktualne_dane['open']} USDT
    - Maksimum 24h (high): {aktualne_dane['high']} USDT
    - Minimum 24h (low): {aktualne_dane['low']} USDT
    - VWAP 24h (średnia ważona wolumenem): {aktualne_dane['vwap']}
    - Zmiana 24h (change / percentage): {aktualne_dane['change']} ({aktualne_dane['percentage']}%)
    - Wolumen 24h: {aktualne_dane['baseVolume']} (w USDT: {aktualne_dane['quoteVolume']})
    - Najlepsza oferta kupna (bid): {aktualne_dane['bid']} (ilość: {aktualne_dane['bidVolume']})
    - Najlepsza oferta sprzedaży (ask): {aktualne_dane['ask']} (ilość: {aktualne_dane['askVolume']})
    - Spread: {_format_procent(aktualne_dane['spread_procent'])}
    - Czas danych (timestamp): {aktualne_dane['timestamp']}
    """


def formatuj_swiece(swiece: pd.DataFrame, interwal: str, liczba: int = SWIECE_W_PROMPCIE) -> str:
    return f"""
    --- HISTORIA ZAMKNIĘTYCH ŚWIEC (ostatnie {liczba} z interwału {interwal}, czas UTC) ---
    {swiece.tail(liczba).to_string(index=False)}
    """
