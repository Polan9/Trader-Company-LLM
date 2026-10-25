"""Raport skuteczności symulacji: python -m symulacja.raport

Porównuje ławę z dwiema strategiami odniesienia (z tych samych rund):
- „zawsze wchodź” — transakcja referencyjna w każdej rundzie (SL 1×ATR, minimalny TP po kosztach),
- „heurystyka” — referencja tylko w rundach z sygnałem wejścia z RSI/MACD/wolumenu,
oraz z kupieniem i trzymaniem: BTC jako benchmark rynku i średnia „kup przy pierwszej rundzie
na danej parze, trzymaj do teraz” (po kosztach wejścia i wyjścia)."""
import sqlite3
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd

from dane.gielda import aktualne_ceny, pobierz_swiece_od
from konfiguracja.ustawienia import PLIK_BAZY
from lawa.sl_tp import koszt_transakcji_procent
from zapis import baza

PARA_BENCHMARKU = "BTC/USDT"

MIN_TRANSAKCJI_DO_WNIOSKOW = 100  # przy ~0.25 R przewagi i odch. 1.25 R — ok. 2σ


def statystyki_transakcji(wyniki_r: pd.Series) -> dict:
    if wyniki_r.empty:
        return {"liczba": 0}
    zyski, straty = wyniki_r[wyniki_r > 0].sum(), -wyniki_r[wyniki_r < 0].sum()
    return {
        "liczba": int(len(wyniki_r)),
        "skutecznosc_procent": float((wyniki_r > 0).mean() * 100),
        "sredni_r": float(wyniki_r.mean()),
        "suma_r": float(wyniki_r.sum()),
        "profit_factor": float(zyski / straty) if straty > 0 else float("inf"),
    }


def maks_spadek_procent(kapital: pd.Series) -> float:
    szczyt = kapital.cummax()
    return float(((kapital - szczyt) / szczyt * 100).min()) if not kapital.empty else 0.0


def kup_i_trzymaj_btc(rundy: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """Benchmark rynku: zamknięcie BTC w świecy pierwszej rundy → ostatnia zamknięta świeca BTC."""
    if rundy.empty:
        return None
    od = pd.Timestamp(rundy["czas_swiecy"].min())
    swiece = pobierz_swiece_od(PARA_BENCHMARKU, rundy["interwal"].iloc[0], od)
    if swiece.empty:
        return None
    start, koniec = float(swiece["close"].iloc[0]), float(swiece["close"].iloc[-1])
    return {"start": start, "koniec": koniec, "zmiana_procent": (koniec / start - 1) * 100,
            "netto_procent": (koniec / start - 1) * 100 - koszt_transakcji_procent(0.0)}


def kup_i_trzymaj_pary(rundy: pd.DataFrame) -> pd.DataFrame:
    """Dla każdej analizowanej pary: kupno po cenie z pierwszej rundy na niej, wycena po aktualnej cenie,
    wynik netto po koszcie wejścia i wyjścia z tej rundy."""
    zwolane = rundy[(rundy["pominieta"] == 0) & rundy["cena_wejscia"].notna()]
    if zwolane.empty:
        return pd.DataFrame()
    pierwsze = zwolane.sort_values("czas_swiecy").groupby("symbol", as_index=False).first()
    ceny = aktualne_ceny(list(pierwsze["symbol"]))
    pierwsze["cena_teraz"] = pierwsze["symbol"].map(ceny)
    pierwsze = pierwsze.dropna(subset=["cena_teraz"])
    pierwsze["zmiana_procent"] = (pierwsze["cena_teraz"] / pierwsze["cena_wejscia"] - 1) * 100
    pierwsze["netto_procent"] = pierwsze["zmiana_procent"] - pierwsze["koszt_procent"]
    return pierwsze[["symbol", "czas_swiecy", "cena_wejscia", "cena_teraz", "zmiana_procent", "netto_procent"]]


def otwarte_oceny_na_zywo(polaczenie: sqlite3.Connection) -> pd.DataFrame:
    """Nierozstrzygnięte transakcje hipotetyczne wycenione po aktualnej cenie (niezrealizowany wynik)."""
    oceny = baza.tabela_jako_df(polaczenie, """
        SELECT oc.id, oc.runda_id, oc.kto, oc.symbol, oc.czas_wejscia, oc.cena_wejscia,
               oc.stop_loss, oc.take_profit, oc.koszt_procent, o.nazwa
        FROM oceny oc
        LEFT JOIN opinie o ON o.runda_id = oc.runda_id AND o.trader_id = oc.kto
        WHERE oc.status = 'otwarta' ORDER BY oc.czas_wejscia, oc.id
    """)
    if oceny.empty:
        return oceny
    ceny = aktualne_ceny(sorted(oceny["symbol"].unique()))
    oceny["cena_teraz"] = oceny["symbol"].map(ceny)
    oceny["kto"] = oceny["nazwa"].fillna(oceny["kto"])
    ryzyko = (oceny["cena_wejscia"] - oceny["stop_loss"]) / oceny["cena_wejscia"] * 100 + oceny["koszt_procent"]
    oceny["wynik_procent"] = (oceny["cena_teraz"] / oceny["cena_wejscia"] - 1) * 100 - oceny["koszt_procent"]
    oceny["wynik_r"] = oceny["wynik_procent"] / ryzyko
    oceny["do_sl_procent"] = (oceny["cena_teraz"] / oceny["stop_loss"] - 1) * 100
    oceny["do_tp_procent"] = (oceny["take_profit"] / oceny["cena_teraz"] - 1) * 100
    oceny["godzin_otwarta"] = (
        (pd.Timestamp.now(tz="UTC") - pd.to_datetime(oceny["czas_wejscia"], utc=True)).dt.total_seconds() / 3600
    )
    return oceny


def formatuj_otwarte_oceny(oceny: pd.DataFrame) -> str:
    if oceny.empty:
        return "  brak otwartych ocen"
    linie = [f"  {'para':<11} {'kto':<38} {'wejście':>11} {'teraz':>11} {'wynik':>8} {'R':>6} "
             f"{'do SL':>7} {'do TP':>7} {'godz.':>5}"]
    for w in oceny.itertuples(index=False):
        if pd.isna(w.cena_teraz):
            linie.append(f"  {w.symbol:<11} {w.kto:<38} brak aktualnej ceny")
            continue
        linie.append(
            f"  {w.symbol:<11} {w.kto:<38} {w.cena_wejscia:>11.6g} {w.cena_teraz:>11.6g} {w.wynik_procent:>+7.2f}% "
            f"{w.wynik_r:>+6.2f} {w.do_sl_procent:>6.2f}% {w.do_tp_procent:>6.2f}% {w.godzin_otwarta:>5.1f}"
        )
    referencje = oceny[oceny["kto"] == "referencja"]
    linie.append(f"  Razem {len(oceny)} (referencje: {len(referencje)}, głosy TAK: {len(oceny) - len(referencje)}) | "
                 f"średnio {oceny['wynik_r'].mean():+.2f} R niezrealizowane")
    return "\n".join(linie)


def _linia_statystyk(nazwa: str, s: dict) -> str:
    if not s["liczba"]:
        return f"  {nazwa:<22} brak rozstrzygniętych transakcji"
    return (f"  {nazwa:<22} n={s['liczba']:<4} skuteczność {s['skutecznosc_procent']:5.1f}% | "
            f"średnio {s['sredni_r']:+.3f} R | suma {s['suma_r']:+.2f} R | PF {s['profit_factor']:.2f}")


def karta_traderow(polaczenie: sqlite3.Connection) -> pd.DataFrame:
    """Trafność traderów: TAK trafny, gdy własna transakcja zarobiła; NIE trafny, gdy referencja straciła."""
    opinie = baza.tabela_jako_df(polaczenie, """
        SELECT o.runda_id, o.trader_id, o.nazwa, o.glos,
               wlasna.status AS status_wlasnej, wlasna.wynik_r AS wynik_r_wlasny,
               ref.status AS status_ref, ref.wynik_r AS wynik_r_ref
        FROM opinie o
        LEFT JOIN oceny wlasna ON wlasna.runda_id = o.runda_id AND wlasna.kto = o.trader_id
        LEFT JOIN oceny ref ON ref.runda_id = o.runda_id AND ref.kto = 'referencja'
    """)
    if opinie.empty:
        return opinie
    tak = opinie["glos"] == "TAK"
    opinie["rozstrzygnieta"] = np.where(tak, opinie["status_wlasnej"] == "zamknieta", opinie["status_ref"] == "zamknieta")
    opinie["trafna"] = np.where(tak, opinie["wynik_r_wlasny"] > 0, opinie["wynik_r_ref"] <= 0)

    wiersze = []
    for (trader_id, nazwa), grupa in opinie.groupby(["trader_id", "nazwa"]):
        ocenione = grupa[grupa["rozstrzygnieta"]]
        ocenione_tak = ocenione[ocenione["glos"] == "TAK"]
        ocenione_nie = ocenione[ocenione["glos"] == "NIE"]
        wiersze.append({
            "trader": nazwa,
            "glosy": len(grupa),
            "tak_procent": (grupa["glos"] == "TAK").mean() * 100,
            "rozstrzygniete": len(ocenione),
            "trafnosc_procent": ocenione["trafna"].mean() * 100 if len(ocenione) else np.nan,
            "trafnosc_tak_procent": ocenione_tak["trafna"].mean() * 100 if len(ocenione_tak) else np.nan,
            "sredni_r_tak": ocenione_tak["wynik_r_wlasny"].mean() if len(ocenione_tak) else np.nan,
            "trafnosc_nie_procent": ocenione_nie["trafna"].mean() * 100 if len(ocenione_nie) else np.nan,
        })
    return pd.DataFrame(wiersze).sort_values("trafnosc_procent", ascending=False)


def zbuduj_raport(polaczenie: sqlite3.Connection) -> str:
    rundy = baza.tabela_jako_df(polaczenie, "SELECT * FROM rundy ORDER BY czas_swiecy")
    pozycje = baza.tabela_jako_df(polaczenie, "SELECT * FROM pozycje ORDER BY czas_wejscia")
    oceny_ref = baza.tabela_jako_df(polaczenie, """
        SELECT oc.*, r.ma_sygnal_heurystyczny FROM oceny oc JOIN rundy r ON r.id = oc.runda_id
        WHERE oc.kto = 'referencja' AND oc.status = 'zamknieta'
    """)
    start = baza.budzet_poczatkowy(polaczenie)
    budzet = baza.aktualny_budzet(polaczenie)
    koszt_llm = float(rundy["koszt_llm_usd"].sum()) if not rundy.empty else 0.0

    linie = ["=== RAPORT SYMULACJI ==="]
    if rundy.empty:
        return "\n".join(linie + ["Brak rund w bazie."])

    zwolane = rundy[rundy["pominieta"] == 0]
    linie += [
        f"Okres: {rundy['czas_swiecy'].iloc[0]} → {rundy['czas_swiecy'].iloc[-1]}",
        f"Rundy: {len(rundy)} (ława zwołana: {len(zwolane)}, pominięte przy otwartej pozycji: {len(rundy) - len(zwolane)})",
        f"Decyzje ławy TAK: {(zwolane['decyzja_lawy'] == 'TAK').sum()} | otwarte pozycje: {int(zwolane['otworz_pozycje'].sum())}",
        "",
        "PORTFEL",
        f"  Budżet: {start:.2f} → {budzet:.2f} USD ({(budzet / start - 1) * 100:+.2f}%)",
        f"  Koszt LLM: ${koszt_llm:.4f} | wynik po kosztach LLM: {budzet - start - koszt_llm:+.2f} USD",
    ]

    zamkniete = pozycje[pozycje["status"] == "zamknieta"] if not pozycje.empty else pozycje
    linie += ["", "TRANSAKCJE ŁAWY (po kosztach)"]
    if zamkniete.empty:
        linie.append("  brak zamkniętych transakcji")
    else:
        linie.append(_linia_statystyk("Ława", statystyki_transakcji(zamkniete["wynik_r"])))
        kapital = start + zamkniete.sort_values("czas_wyjscia")["wynik_usd"].cumsum()
        czas_trwania = (pd.to_datetime(zamkniete["czas_wyjscia"]) - pd.to_datetime(zamkniete["czas_wejscia"])).mean()
        powody = zamkniete["powod"].value_counts().to_dict()
        linie += [
            f"  Maks. spadek kapitału: {maks_spadek_procent(pd.concat([pd.Series([start]), kapital])):.2f}%",
            f"  Średni czas pozycji: {czas_trwania} | wyjścia: {powody}",
        ]
    otwarte = int((pozycje["status"] == "otwarta").sum()) if not pozycje.empty else 0
    linie.append(f"  Otwarte pozycje: {otwarte}")

    linie += ["", "STRATEGIE ODNIESIENIA (te same rundy)"]
    linie.append(_linia_statystyk("Zawsze wchodź", statystyki_transakcji(oceny_ref["wynik_r"])))
    heurystyka = oceny_ref[oceny_ref["ma_sygnal_heurystyczny"] == 1]
    linie.append(_linia_statystyk("Heurystyka RSI/MACD", statystyki_transakcji(heurystyka["wynik_r"])))
    try:
        btc = kup_i_trzymaj_btc(rundy)
        pary = kup_i_trzymaj_pary(rundy)
    except Exception as blad:  # raport ma działać także bez dostępu do giełdy
        linie.append(f"  Kup i trzymaj:          brak danych z giełdy ({blad})")
    else:
        if btc:
            linie.append(f"  Kup i trzymaj BTC:      {btc['zmiana_procent']:+.2f}% "
                         f"({btc['start']:.2f} → {btc['koniec']:.2f}; netto po kosztach {btc['netto_procent']:+.2f}%)")
        if not pary.empty:
            linie.append(f"  Kup i trzymaj pary:     średnio {pary['netto_procent'].mean():+.2f}% netto "
                         f"({len(pary)} par; kupno przy pierwszej rundzie na danej parze)")
            for w in pary.sort_values("netto_procent", ascending=False).itertuples(index=False):
                linie.append(f"    {w.symbol:<12} {w.cena_wejscia:.8g} → {w.cena_teraz:.8g}: "
                             f"{w.zmiana_procent:+.2f}% (netto {w.netto_procent:+.2f}%)")

    linie += ["", "OTWARTE OCENY — wycena na żywo (wynik netto po kosztach; R = wynik / ryzyko do SL)"]
    try:
        linie.append(formatuj_otwarte_oceny(otwarte_oceny_na_zywo(polaczenie)))
    except Exception as blad:
        linie.append(f"  brak danych z giełdy ({blad})")

    karta = karta_traderow(polaczenie)
    linie += ["", "KARTA TRADERÓW (TAK trafny = własna transakcja na plus; NIE trafny = referencja na minus)"]
    if karta.empty:
        linie.append("  brak opinii")
    else:
        for w in karta.itertuples(index=False):
            def p(x, fmt="{:5.1f}%"):
                return "  —  " if pd.isna(x) else fmt.format(x)
            linie.append(
                f"  {w.trader:<38} głosy {w.glosy:<4} TAK {w.tak_procent:5.1f}% | rozstrzygnięte {w.rozstrzygniete:<4} "
                f"trafność {p(w.trafnosc_procent)} (TAK {p(w.trafnosc_tak_procent)}, NIE {p(w.trafnosc_nie_procent)}) "
                f"| śr. R z TAK {p(w.sredni_r_tak, '{:+.3f}')}"
            )

    liczba = len(zamkniete)
    if liczba < MIN_TRANSAKCJI_DO_WNIOSKOW:
        linie += ["", f"UWAGA: {liczba} zamkniętych transakcji — za mało na wnioski "
                      f"(potrzeba ok. {MIN_TRANSAKCJI_DO_WNIOSKOW}). Wyniki mogą być przypadkowe."]
    return "\n".join(linie)


if __name__ == "__main__":
    if not PLIK_BAZY.exists():
        print(f"Brak bazy {PLIK_BAZY} — najpierw uruchom symulator: python -m symulacja")
    else:
        polaczenie = baza.polacz(PLIK_BAZY)
        print(zbuduj_raport(polaczenie))
        polaczenie.close()
