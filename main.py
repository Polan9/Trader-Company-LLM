from pathlib import Path
from typing import Any, Dict, TypedDict

import ccxt
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

# --- Konfiguracja ---
KATALOG_PROJEKTU = Path(__file__).resolve().parent
PLIK_STANU = KATALOG_PROJEKTU / "trading_state.txt"

SYMBOL = "BTC/USDT"
INTERWAL = "15m"
BUDZET_POCZATKOWY = 1000.0
MODEL_ANALITYKA = "gpt-4o-mini"

# Wskaźniki wygładzane wykładniczo potrzebują "rozgrzewki" — im więcej świec,
# tym mniejszy wpływ wartości startowej (przy 300 świecach błąd jest pomijalny).
LIMIT_SWIEC = 300
MIN_SWIEC = 100
OKRES_RSI = 14
MACD_SZYBKI = 12
MACD_WOLNY = 26
MACD_SYGNAL = 9
OKRES_SREDNIEGO_WOLUMENU = 20
OKRES_TRENDU_WOLUMENU = 5
PROG_TRENDU_WOLUMENU = 5.0  # % zmiany na świecę (nachylenie prostej)
SWIECE_W_PROMPCIE = 25

load_dotenv(KATALOG_PROJEKTU / ".env")
llm_analityka = ChatOpenAI(model=MODEL_ANALITYKA, temperature=0)


class AktualnyStan(TypedDict):
    symbol: str
    interwal: str
    aktualne_dane: Dict[str, Any]
    dane_historyczne: pd.DataFrame
    analiza_techniczna: Dict[str, Any]
    decyzja_analityka: str
    decyzja_head_tradera: str
    budzet: float


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


def _ema(seria: pd.Series, okres: int) -> pd.Series:
    return _wygladz(seria, okres, alpha=2 / (okres + 1))


def _rma(seria: pd.Series, okres: int) -> pd.Series:
    """Średnia Wildera — używana w klasycznym RSI."""
    return _wygladz(seria, okres, alpha=1 / okres)


def _rsi(zamkniecia: pd.Series, okres: int = OKRES_RSI) -> pd.Series:
    delta = zamkniecia.diff()
    sredni_zysk = _rma(delta.clip(lower=0), okres)
    srednia_strata = _rma(-delta.clip(upper=0), okres)
    rsi = 100 - 100 / (1 + sredni_zysk / srednia_strata)
    rsi = rsi.where(srednia_strata != 0, 100.0)  # same wzrosty
    rsi = rsi.where(~((sredni_zysk == 0) & (srednia_strata == 0)), 50.0)  # brak ruchu
    return rsi


def _macd(zamkniecia: pd.Series, szybki: int = MACD_SZYBKI, wolny: int = MACD_WOLNY, sygnal: int = MACD_SYGNAL):
    linia = _ema(zamkniecia, szybki) - _ema(zamkniecia, wolny)
    linia_sygnalu = _ema(linia, sygnal)
    histogram = linia - linia_sygnalu
    return linia, linia_sygnalu, histogram


def _nachylenie_procentowe(seria: pd.Series) -> float:
    """Nachylenie prostej dopasowanej do serii, w % średniej na jedną świecę."""
    srednia = float(seria.mean())
    if srednia == 0:
        return 0.0
    nachylenie = np.polyfit(np.arange(len(seria)), seria.to_numpy(dtype=float), 1)[0]
    return float(nachylenie / srednia * 100)


def oblicz_analize_techniczna(stan: AktualnyStan):
    print("----Analiza techniczna (wolumen, RSI, MACD)----")
    swiece = stan["dane_historyczne"]
    if not isinstance(swiece, pd.DataFrame) or swiece.empty:
        raise RuntimeError("Brak danych historycznych do analizy technicznej.")
    if len(swiece) < MIN_SWIEC:
        raise RuntimeError(
            f"Za mało świec do wiarygodnych wskaźników ({len(swiece)} < {MIN_SWIEC}; zwiększ LIMIT_SWIEC)."
        )

    zamkniecia = swiece["close"].astype(float)
    wolumen = swiece["volume"].astype(float)

    rsi_seria = _rsi(zamkniecia)
    macd_linia, macd_sygnal, macd_hist = _macd(zamkniecia)
    # Średnia z poprzednich świec — bez bieżącej, żeby nie porównywać świecy z samą sobą
    sredni_wolumen = wolumen.shift(1).rolling(OKRES_SREDNIEGO_WOLUMENU).mean()

    rsi_akt = float(rsi_seria.iloc[-1])
    rsi_pop = float(rsi_seria.iloc[-2])
    macd_akt = float(macd_linia.iloc[-1])
    macd_pop = float(macd_linia.iloc[-2])
    sygnal_akt = float(macd_sygnal.iloc[-1])
    sygnal_pop = float(macd_sygnal.iloc[-2])
    hist_akt = float(macd_hist.iloc[-1])
    hist_pop = float(macd_hist.iloc[-2])
    wol_akt = float(wolumen.iloc[-1])
    wol_pop = float(wolumen.iloc[-2])
    wol_srednia = float(sredni_wolumen.iloc[-1])

    if np.isnan([rsi_akt, rsi_pop, macd_akt, macd_pop, sygnal_akt, sygnal_pop, wol_srednia]).any():
        raise RuntimeError("Wskaźniki zwróciły NaN — za mało danych lub błędne świece.")

    zmiana_wol_vs_pop = ((wol_akt - wol_pop) / wol_pop * 100) if wol_pop else 0.0
    zmiana_wol_vs_srednia = ((wol_akt - wol_srednia) / wol_srednia * 100) if wol_srednia else 0.0

    nachylenie_wolumenu = _nachylenie_procentowe(wolumen.tail(OKRES_TRENDU_WOLUMENU))
    if nachylenie_wolumenu > PROG_TRENDU_WOLUMENU:
        trend_wolumenu = "rosnący"
    elif nachylenie_wolumenu < -PROG_TRENDU_WOLUMENU:
        trend_wolumenu = "malejący"
    else:
        trend_wolumenu = "stabilny"

    if zmiana_wol_vs_srednia > 50:
        sygnal_wolumenu = "wyraźny wzrost aktywności (wolumen powyżej średniej)"
    elif zmiana_wol_vs_srednia < -30:
        sygnal_wolumenu = "niski wolumen względem średniej — słabsze potwierdzenie ruchu"
    else:
        sygnal_wolumenu = "wolumen w okolicy normy"

    if rsi_akt >= 70:
        strefa_rsi = "wykupienie"
        sygnal_rsi = "sygnał ostrożności przy kupnie / rozważ realizację zysków"
    elif rsi_akt <= 30:
        strefa_rsi = "wyprzedanie"
        sygnal_rsi = "możliwy obszar odbicia — szukaj potwierdzenia (MACD, wolumen)"
    else:
        strefa_rsi = "neutralna"
        sygnal_rsi = "brak skrajnego sygnału RSI"

    przeciecie_w_gore = macd_pop <= sygnal_pop and macd_akt > sygnal_akt
    przeciecie_w_dol = macd_pop >= sygnal_pop and macd_akt < sygnal_akt
    if przeciecie_w_gore:
        sygnal_macd = "świeże przecięcie MACD w górę (sygnał byczy)"
    elif przeciecie_w_dol:
        sygnal_macd = "świeże przecięcie MACD w dół (sygnał niedźwiedzi)"
    elif macd_akt > sygnal_akt and hist_akt > hist_pop:
        sygnal_macd = "MACD powyżej linii sygnału, rosnący histogram — momentum bycze"
    elif macd_akt < sygnal_akt and hist_akt < hist_pop:
        sygnal_macd = "MACD poniżej linii sygnału, malejący histogram — momentum niedźwiedzie"
    else:
        sygnal_macd = "MACD bez wyraźnego nowego przecięcia"

    sygnaly_wejscia = []
    sygnaly_wyjscia = []
    if rsi_akt <= 35 and macd_akt > sygnal_akt:
        sygnaly_wejscia.append("RSI nisko + MACD powyżej sygnału")
    if rsi_akt <= 30:
        sygnaly_wejscia.append("RSI w strefie wyprzedania")
    if przeciecie_w_gore and zmiana_wol_vs_srednia > 0:
        sygnaly_wejscia.append("bycze MACD przy wzroście wolumenu")
    if rsi_akt >= 65:
        sygnaly_wyjscia.append("RSI zbliżony do wykupienia")
    if przeciecie_w_dol:
        sygnaly_wyjscia.append("niedźwiedzie przecięcie MACD")
    if rsi_akt >= 70:
        sygnaly_wyjscia.append("RSI w wykupieniu")

    # Wartości bez zaokrągleń — formatowanie dopiero przy wyświetlaniu,
    # żeby nie tracić precyzji przy tanich coinach (np. cena 0.0001).
    analiza = {
        "czas_ostatniej_swiecy": swiece["timestamp"].iloc[-1],
        "wolumen": {
            "ostatnia_swieca": wol_akt,
            "poprzednia_swieca": wol_pop,
            "srednia_poprzednich": wol_srednia,
            "okres_sredniej": OKRES_SREDNIEGO_WOLUMENU,
            "zmiana_procent_vs_poprzednia": zmiana_wol_vs_pop,
            "zmiana_procent_vs_srednia": zmiana_wol_vs_srednia,
            "nachylenie_procent_na_swiece": nachylenie_wolumenu,
            "trend": trend_wolumenu,
            "interpretacja": sygnal_wolumenu,
        },
        "rsi": {
            "okres": OKRES_RSI,
            "wartosc": rsi_akt,
            "poprzednia_wartosc": rsi_pop,
            "strefa": strefa_rsi,
            "interpretacja": sygnal_rsi,
        },
        "macd": {
            "parametry": (MACD_SZYBKI, MACD_WOLNY, MACD_SYGNAL),
            "linia_macd": macd_akt,
            "linia_sygnalu": sygnal_akt,
            "histogram": hist_akt,
            "poprzedni_histogram": hist_pop,
            "interpretacja": sygnal_macd,
        },
        "moment_wejscia_wyjscia": {
            "sygnaly_wejscia": sygnaly_wejscia or ["brak mocnych sygnałów wejścia"],
            "sygnaly_wyjscia": sygnaly_wyjscia or ["brak mocnych sygnałów wyjścia"],
        },
    }
    return {"analiza_techniczna": analiza}


def _format_analiza_techniczna_do_promptu(analiza: Dict[str, Any]) -> str:
    if not analiza:
        return "(brak analizy technicznej)"
    w = analiza["wolumen"]
    r = analiza["rsi"]
    m = analiza["macd"]
    mw = analiza["moment_wejscia_wyjscia"]
    wejscia = ", ".join(mw["sygnaly_wejscia"])
    wyjscia = ", ".join(mw["sygnaly_wyjscia"])
    szybki, wolny, sygnal = m["parametry"]
    return f"""
    --- ANALIZA TECHNICZNA (ostatnia zamknięta świeca: {analiza['czas_ostatniej_swiecy']}) ---
    WOLUMEN:
    - Ostatnia świeca: {w['ostatnia_swieca']:.6g} | Poprzednia: {w['poprzednia_swieca']:.6g}
    - Średnia z {w['okres_sredniej']} poprzednich świec: {w['srednia_poprzednich']:.6g}
    - Zmiana vs poprzednia świeca: {w['zmiana_procent_vs_poprzednia']:.2f}%
    - Zmiana vs średnia: {w['zmiana_procent_vs_srednia']:.2f}%
    - Trend wolumenu (5 świec): {w['trend']} ({w['nachylenie_procent_na_swiece']:+.2f}% na świecę)
    - Interpretacja: {w['interpretacja']}

    RSI ({r['okres']} okresów, Wilder):
    - Wartość: {r['wartosc']:.2f} (poprzednio: {r['poprzednia_wartosc']:.2f})
    - Strefa: {r['strefa']}
    - Interpretacja: {r['interpretacja']}

    MACD ({szybki}, {wolny}, {sygnal}):
    - Linia MACD: {m['linia_macd']:.6g} | Sygnał: {m['linia_sygnalu']:.6g} | Histogram: {m['histogram']:.6g}
    - Poprzedni histogram: {m['poprzedni_histogram']:.6g}
    - Interpretacja: {m['interpretacja']}

    SYGNAŁY WEJŚCIA / WYJŚCIA (heurystyka):
    - Wejście: {wejscia}
    - Wyjście: {wyjscia}
    """


def _format_procent(wartosc) -> str:
    return f"{wartosc:.4f}%" if wartosc is not None else "brak"


def analityk(stan: AktualnyStan):
    print("----Analityk----")
    aktualne_dane = stan["aktualne_dane"]
    dane_historyczne = stan["dane_historyczne"]

    if not aktualne_dane or aktualne_dane.get("last") is None:
        raise RuntimeError(
            "Brak danych rynkowych w stanie — węzeł 'pobierz_dane' nie uzupełnił aktualne_dane."
        )

    prompt = f"""
    Jesteś profesjonalnym analitykiem rynku kryptowalut, twoim zadaniem jest:
    - analiza danej pary i dostępnych danych,
    - propozycja ruchu na giełdzie,
    - podjęcie wstępnej decyzji,
    - przygotowanie raportu z propozycjami dla head tradera.

    Para: {stan["symbol"]}
    Interwał: {stan["interwal"]}
    Aktualne dostępne saldo w USD: {stan["budzet"]}

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

    {_format_analiza_techniczna_do_promptu(stan.get("analiza_techniczna", {}))}

    --- HISTORIA ZAMKNIĘTYCH ŚWIEC (ostatnie {SWIECE_W_PROMPCIE} z interwału {stan["interwal"]}, czas UTC) ---
    {dane_historyczne.tail(SWIECE_W_PROMPCIE).to_string(index=False)}

    Uwzględnij szczególnie analizę techniczną (wolumen, RSI, MACD) przy ocenie momentów wejścia i wyjścia.

    Przeanalizuj te dane i podaj decyzję inwestycyjną w formacie:
    1. DECYZJA: [KUPUJ / SPRZEDAJ / CZEKAJ]
    2. UZASADNIENIE: wyjaśnienie dla kolejnych osób w zespole.
    3. POZIOM STOP-LOSS: sugerowana cena zabezpieczenia.
    4. POZIOM TAKE-PROFIT: sugerowane wyjście z pozycji oraz potencjalny zarobek.
    5. WIELKOŚĆ POZYCJI: za ile USD z budżetu otworzyć pozycję.

    JEŚLI PODCZAS ANALIZY BRAKUJE CI DANYCH, NARZĘDZI LUB CZEGOKOLWIEK, CO POMOGŁOBY W ANALIZIE, DOPISZ TO NA SAMYM KOŃCU.
    """

    odpowiedz = llm_analityka.invoke([HumanMessage(content=prompt)])
    print("Analiza zakończona.")
    return {"decyzja_analityka": odpowiedz.content}


def zbuduj_graf():
    graf = StateGraph(AktualnyStan)

    graf.add_node("pobierz_dane", pobierz_dane)
    graf.add_node("analiza_techniczna", oblicz_analize_techniczna)
    graf.add_node("analityk", analityk)

    graf.add_edge(START, "pobierz_dane")
    graf.add_edge("pobierz_dane", "analiza_techniczna")
    graf.add_edge("analiza_techniczna", "analityk")
    graf.add_edge("analityk", END)

    return graf.compile()


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
        linie.append(_format_analiza_techniczna_do_promptu(analiza).strip())
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


if __name__ == "__main__":
    stan_poczatkowy: AktualnyStan = {
        "symbol": SYMBOL,
        "interwal": INTERWAL,
        "aktualne_dane": {},
        "dane_historyczne": pd.DataFrame(),
        "analiza_techniczna": {},
        "decyzja_analityka": "",
        "decyzja_head_tradera": "",
        "budzet": BUDZET_POCZATKOWY,
    }

    aplikacja = zbuduj_graf()
    wynik = aplikacja.invoke(stan_poczatkowy)
    zapisz_stan(wynik)
