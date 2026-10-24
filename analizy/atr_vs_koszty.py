"""Analiza: czy zmienność (ATR) na danym interwale pokrywa koszty transakcji.

Dla najpłynniejszych par USDT na Binance spot liczy medianę ATR% (ATR / cena)
na kilku interwałach i porównuje z kosztem wejścia + wyjścia (prowizje + spread).
Uruchomienie z katalogu głównego: .venv\\Scripts\\python.exe -m analizy.atr_vs_koszty
"""
import ccxt
import pandas as pd

from wskazniki.obliczenia import atr

LICZBA_COINOW = 30
INTERWALY = ["5m", "15m", "1h", "4h"]
LIMIT_SWIEC = 1000  # maks. na jedno zapytanie Binance
ROZGRZEWKA = 50  # pierwsze wartości ATR pomijane (start wygładzania)
PROWIZJA_STRONA = 0.10  # % za jedną stronę (taker, bez zniżki BNB)
PROWIZJA_STRONA_BNB = 0.075  # % z opłatą w BNB
SL_ATR = 1.0  # stop-loss w wielokrotnościach ATR
TP_ATR = 1.5  # take-profit w wielokrotnościach ATR (zysk/ryzyko = 1.5)

STABLECOINY = {
    "USDC", "FDUSD", "TUSD", "DAI", "USDP", "BUSD", "USDE", "PYUSD", "USD1",
    "BFUSD", "XUSD", "EUR", "AEUR", "EURI", "USDS", "RLUSD", "PAXG", "WBTC", "WBETH",
}


def _najplynniejsze_pary(gielda: ccxt.Exchange, liczba: int) -> pd.DataFrame:
    rynki = gielda.load_markets()
    tickery = gielda.fetch_tickers()
    wiersze = []
    for symbol, ticker in tickery.items():
        rynek = rynki.get(symbol)
        if not rynek or not rynek.get("spot") or not rynek.get("active"):
            continue
        if rynek["quote"] != "USDT" or rynek["base"] in STABLECOINY:
            continue
        bid, ask = ticker.get("bid"), ticker.get("ask")
        if not bid or not ask:
            continue
        wiersze.append({
            "symbol": symbol,
            "wolumen_usdt_24h": ticker.get("quoteVolume") or 0,
            "spread_procent": (ask - bid) / ((ask + bid) / 2) * 100,
        })
    pary = pd.DataFrame(wiersze).sort_values("wolumen_usdt_24h", ascending=False)
    return pary.head(liczba).reset_index(drop=True)


def _mediana_atr_procent(gielda: ccxt.Exchange, symbol: str, interwal: str) -> float:
    surowe = gielda.fetch_ohlcv(symbol, interwal, limit=LIMIT_SWIEC)
    swiece = pd.DataFrame(surowe, columns=["timestamp", "open", "high", "low", "close", "volume"])
    swiece = swiece.iloc[:-1]  # bez trwającej świecy
    atr_procent = atr(swiece) / swiece["close"] * 100
    return float(atr_procent.iloc[ROZGRZEWKA:].median())


def _wymagana_skutecznosc(atr_procent: float, koszt_procent: float) -> float:
    """Win rate potrzebny do wyjścia na zero przy SL = SL_ATR·ATR i TP = TP_ATR·ATR.
    p·(TP − k) = (1 − p)·(SL + k)  →  p = (SL + k) / (TP + SL)."""
    koszt_w_atr = koszt_procent / atr_procent
    return (SL_ATR + koszt_w_atr) / (TP_ATR + SL_ATR) * 100


def main():
    gielda = ccxt.binance({"enableRateLimit": True})
    pary = _najplynniejsze_pary(gielda, LICZBA_COINOW)

    for interwal in INTERWALY:
        print(f"Pobieranie {interwal}...")
        pary[f"atr_{interwal}"] = [_mediana_atr_procent(gielda, s, interwal) for s in pary["symbol"]]

    pary["koszt"] = 2 * PROWIZJA_STRONA + pary["spread_procent"]
    pary["koszt_bnb"] = 2 * PROWIZJA_STRONA_BNB + pary["spread_procent"]
    for interwal in INTERWALY:
        pary[f"wr_{interwal}"] = [
            _wymagana_skutecznosc(a, k) for a, k in zip(pary[f"atr_{interwal}"], pary["koszt"])
        ]

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    widok = pary.copy()
    widok["wolumen_mln"] = widok["wolumen_usdt_24h"] / 1e6
    kolumny = (["symbol", "wolumen_mln", "spread_procent", "koszt"]
               + [f"atr_{i}" for i in INTERWALY] + [f"wr_{i}" for i in INTERWALY])
    print("\nATR% = mediana ATR(14)/cena; koszt = 2×prowizja + spread [%]; "
          f"wr = wymagany win rate [%] przy SL={SL_ATR}·ATR, TP={TP_ATR}·ATR (bez kosztów: "
          f"{SL_ATR / (SL_ATR + TP_ATR) * 100:.0f}%)\n")
    print(widok[kolumny].to_string(index=False, float_format=lambda x: f"{x:.3f}"))

    print("\nPODSUMOWANIE (mediana po coinach):")
    for interwal in INTERWALY:
        atr_med = pary[f"atr_{interwal}"].median()
        koszt_w_atr = (pary["koszt"] / pary[f"atr_{interwal}"]).median() * 100
        koszt_bnb_w_atr = (pary["koszt_bnb"] / pary[f"atr_{interwal}"]).median() * 100
        print(f"  {interwal:>3}: ATR {atr_med:.3f}% | koszt = {koszt_w_atr:.0f}% ATR "
              f"(z BNB {koszt_bnb_w_atr:.0f}%) | wymagany win rate {pary[f'wr_{interwal}'].median():.1f}%")

    pary.to_csv("analizy/atr_vs_koszty_wynik.csv", index=False)
    print("\nZapisano: analizy/atr_vs_koszty_wynik.csv")


if __name__ == "__main__":
    main()
