"""Raport skuteczności symulacji: python -m symulacja.raport

Porównuje ławę z dwiema strategiami odniesienia (z tych samych rund):
- „zawsze wchodź” — transakcja referencyjna w każdej rundzie (SL 1×ATR, minimalny TP po kosztach),
- „heurystyka” — referencja tylko w rundach z sygnałem wejścia z RSI/MACD/wolumenu,
oraz z kupieniem i trzymaniem (cena z pierwszej i ostatniej rundy)."""
import sqlite3

import numpy as np
import pandas as pd

from konfiguracja.ustawienia import PLIK_BAZY
from zapis import baza

MIN_TRANSAKCJI_DO_WNIOSKOW = 100  # przy ~0.25 R przewagi i odch. 1.25 R — ok. 2σ


def _statystyki_transakcji(wyniki_r: pd.Series) -> dict:
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


def _maks_spadek_procent(kapital: pd.Series) -> float:
    szczyt = kapital.cummax()
    return float(((kapital - szczyt) / szczyt * 100).min()) if not kapital.empty else 0.0


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
        linie.append(_linia_statystyk("Ława", _statystyki_transakcji(zamkniete["wynik_r"])))
        kapital = start + zamkniete.sort_values("czas_wyjscia")["wynik_usd"].cumsum()
        czas_trwania = (pd.to_datetime(zamkniete["czas_wyjscia"]) - pd.to_datetime(zamkniete["czas_wejscia"])).mean()
        powody = zamkniete["powod"].value_counts().to_dict()
        linie += [
            f"  Maks. spadek kapitału: {_maks_spadek_procent(pd.concat([pd.Series([start]), kapital])):.2f}%",
            f"  Średni czas pozycji: {czas_trwania} | wyjścia: {powody}",
        ]
    otwarte = int((pozycje["status"] == "otwarta").sum()) if not pozycje.empty else 0
    linie.append(f"  Otwarte pozycje: {otwarte}")

    linie += ["", "STRATEGIE ODNIESIENIA (te same rundy)"]
    linie.append(_linia_statystyk("Zawsze wchodź", _statystyki_transakcji(oceny_ref["wynik_r"])))
    heurystyka = oceny_ref[oceny_ref["ma_sygnal_heurystyczny"] == 1]
    linie.append(_linia_statystyk("Heurystyka RSI/MACD", _statystyki_transakcji(heurystyka["wynik_r"])))
    ceny = zwolane["cena_wejscia"].dropna()
    if len(ceny) >= 2:
        linie.append(f"  Kup i trzymaj:          {(ceny.iloc[-1] / ceny.iloc[0] - 1) * 100:+.2f}% (cena pierwszej → ostatniej rundy)")

    karta = karta_traderow(polaczenie)
    linie += ["", "KARTA TRADERÓW (TAK trafny = własna transakcja na plus; NIE trafny = referencja na minus)"]
    if karta.empty:
        linie.append("  brak opinii")
    else:
        for w in karta.itertuples(index=False):
            def p(x, fmt="{:5.1f}%"):
                return "  —  " if pd.isna(x) else fmt.format(x)
            linie.append(
                f"  {w.trader:<30} głosy {w.glosy:<4} TAK {w.tak_procent:5.1f}% | rozstrzygnięte {w.rozstrzygniete:<4} "
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
