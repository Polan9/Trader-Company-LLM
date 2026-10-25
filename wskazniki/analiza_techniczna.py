from typing import Any, Dict

import numpy as np
import pandas as pd

from konfiguracja.ustawienia import (
    MACD_SYGNAL,
    MACD_SZYBKI,
    MACD_WOLNY,
    MIN_SWIEC,
    OKRES_ATR,
    OKRES_RSI,
    OKRES_SREDNIEGO_WOLUMENU,
    OKRES_TRENDU_WOLUMENU,
    PROG_TRENDU_WOLUMENU,
)
from stan import AktualnyStan
from wskazniki.obliczenia import atr, macd, nachylenie_procentowe, rsi
from wskazniki.statystyki import oblicz_statystyki


def oblicz_analize_techniczna(stan: AktualnyStan):
    print("----Analiza techniczna (wolumen, RSI, MACD, ATR)----")
    swiece = stan["dane_historyczne"]
    if not isinstance(swiece, pd.DataFrame) or swiece.empty:
        raise RuntimeError("Brak danych historycznych do analizy technicznej.")
    if len(swiece) < MIN_SWIEC:
        raise RuntimeError(
            f"Za mało świec do wiarygodnych wskaźników ({len(swiece)} < {MIN_SWIEC}; zwiększ LIMIT_SWIEC)."
        )

    zamkniecia = swiece["close"].astype(float)
    wolumen = swiece["volume"].astype(float)

    rsi_seria = rsi(zamkniecia)
    macd_linia, macd_sygnal, macd_hist = macd(zamkniecia)
    atr_seria = atr(swiece)
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
    atr_akt = float(atr_seria.iloc[-1])
    zamkniecie_akt = float(zamkniecia.iloc[-1])
    wol_akt = float(wolumen.iloc[-1])
    wol_pop = float(wolumen.iloc[-2])
    wol_srednia = float(sredni_wolumen.iloc[-1])

    if np.isnan([rsi_akt, rsi_pop, macd_akt, macd_pop, sygnal_akt, sygnal_pop, atr_akt, wol_srednia]).any():
        raise RuntimeError("Wskaźniki zwróciły NaN — za mało danych lub błędne świece.")

    atr_procent = atr_akt / zamkniecie_akt * 100 if zamkniecie_akt else 0.0
    zmiana_wol_vs_pop = ((wol_akt - wol_pop) / wol_pop * 100) if wol_pop else 0.0
    zmiana_wol_vs_srednia = ((wol_akt - wol_srednia) / wol_srednia * 100) if wol_srednia else 0.0

    nachylenie_wolumenu = nachylenie_procentowe(wolumen.tail(OKRES_TRENDU_WOLUMENU))
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
        "atr": {
            "okres": OKRES_ATR,
            "wartosc": atr_akt,
            "procent_ceny": atr_procent,
        },
        "moment_wejscia_wyjscia": {
            "ma_sygnal_wejscia": bool(sygnaly_wejscia),  # strategia odniesienia w raporcie
            "sygnaly_wejscia": sygnaly_wejscia or ["brak mocnych sygnałów wejścia"],
            "sygnaly_wyjscia": sygnaly_wyjscia or ["brak mocnych sygnałów wyjścia"],
        },
        "statystyki": oblicz_statystyki(swiece),
    }
    return {"analiza_techniczna": analiza}


def formatuj_wolumen(analiza: Dict[str, Any]) -> str:
    w = analiza["wolumen"]
    return f"""
    WOLUMEN (ostatnia zamknięta świeca: {analiza['czas_ostatniej_swiecy']}):
    - Ostatnia świeca: {w['ostatnia_swieca']:.6g} | Poprzednia: {w['poprzednia_swieca']:.6g}
    - Średnia z {w['okres_sredniej']} poprzednich świec: {w['srednia_poprzednich']:.6g}
    - Zmiana vs poprzednia świeca: {w['zmiana_procent_vs_poprzednia']:.2f}%
    - Zmiana vs średnia: {w['zmiana_procent_vs_srednia']:.2f}%
    - Trend wolumenu (5 świec): {w['trend']} ({w['nachylenie_procent_na_swiece']:+.2f}% na świecę)
    - Interpretacja: {w['interpretacja']}
    """


def formatuj_rsi(analiza: Dict[str, Any]) -> str:
    r = analiza["rsi"]
    return f"""
    RSI ({r['okres']} okresów, Wilder):
    - Wartość: {r['wartosc']:.2f} (poprzednio: {r['poprzednia_wartosc']:.2f})
    - Strefa: {r['strefa']}
    - Interpretacja: {r['interpretacja']}
    """


def formatuj_macd(analiza: Dict[str, Any]) -> str:
    m = analiza["macd"]
    szybki, wolny, sygnal = m["parametry"]
    return f"""
    MACD ({szybki}, {wolny}, {sygnal}):
    - Linia MACD: {m['linia_macd']:.6g} | Sygnał: {m['linia_sygnalu']:.6g} | Histogram: {m['histogram']:.6g}
    - Poprzedni histogram: {m['poprzedni_histogram']:.6g}
    - Interpretacja: {m['interpretacja']}
    """


def formatuj_atr(analiza: Dict[str, Any]) -> str:
    a = analiza["atr"]
    return f"""
    ATR ({a['okres']} okresów, Wilder) — średni zakres ruchu na świecę:
    - Wartość: {a['wartosc']:.6g} ({a['procent_ceny']:.3f}% ceny zamknięcia)
    """


def formatuj_sygnaly_heurystyczne(analiza: Dict[str, Any]) -> str:
    mw = analiza["moment_wejscia_wyjscia"]
    return f"""
    SYGNAŁY WEJŚCIA / WYJŚCIA (prosta heurystyka z RSI/MACD/wolumenu):
    - Wejście: {", ".join(mw["sygnaly_wejscia"])}
    - Wyjście: {", ".join(mw["sygnaly_wyjscia"])}
    """


def formatuj_analize_techniczna(analiza: Dict[str, Any]) -> str:
    """Pełna analiza — wszystkie bloki razem (np. do zapisu stanu)."""
    if not analiza:
        return "(brak analizy technicznej)"
    bloki = [formatuj_wolumen, formatuj_rsi, formatuj_macd, formatuj_atr, formatuj_sygnaly_heurystyczne]
    return "".join(blok(analiza) for blok in bloki)
