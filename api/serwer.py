"""Serwer interfejsu: API JSON (tylko odczyt) + zbudowany frontend z interfejs/dist.

Uruchomienie: python -m api  (adres i port: API_HOST / API_PORT w konfiguracji)."""
import math
import sqlite3
from typing import Any, Iterator, Optional

import numpy as np
import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from dane.gielda import pobierz_swiece_od
from konfiguracja.lawa import wczytaj_konfiguracje_lawy
from konfiguracja.ustawienia import INTERWAL, KATALOG_INTERFEJSU, MAKS_PAR_NA_SWIECE, PLIK_BAZY
from symulacja.raport import (
    karta_traderow,
    kup_i_trzymaj_btc,
    kup_i_trzymaj_pary,
    maks_spadek_procent,
    statystyki_transakcji,
    trafnosc_wg_pewnosci,
)
from zapis import baza, odczyt

aplikacja = FastAPI(title="Trader Company API")
# Serwer deweloperski Vite (npm run dev) działa na innym porcie
aplikacja.add_middleware(
    CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["GET"],
)


def do_json(wartosc: Any) -> Any:
    """Zamienia NaN/inf na None oraz typy numpy/pandas na zwykłe typy Pythona (JSON bez błędów)."""
    if isinstance(wartosc, dict):
        return {klucz: do_json(w) for klucz, w in wartosc.items()}
    if isinstance(wartosc, (list, tuple)):
        return [do_json(w) for w in wartosc]
    if isinstance(wartosc, (np.integer,)):
        return int(wartosc)
    if isinstance(wartosc, (float, np.floating)):
        return None if math.isnan(wartosc) or math.isinf(wartosc) else float(wartosc)
    if isinstance(wartosc, pd.Timestamp):
        return wartosc.isoformat()
    if isinstance(wartosc, pd.DataFrame):
        return do_json(wartosc.to_dict(orient="records"))
    return wartosc


def polaczenie_bazy() -> Iterator[sqlite3.Connection]:
    if not PLIK_BAZY.exists():
        raise HTTPException(503, f"Brak bazy {PLIK_BAZY} — uruchom symulator (python -m symulacja).")
    polaczenie = odczyt.polacz_do_odczytu(PLIK_BAZY)
    try:
        yield polaczenie
    finally:
        polaczenie.close()


@aplikacja.get("/api/stan")
def stan(polaczenie: sqlite3.Connection = Depends(polaczenie_bazy)):
    wynik = odczyt.stan_portfela(polaczenie)
    ostatnia = wynik["ostatnia_iteracja_ms"]
    # Interfejs odtwarza nową iterację dopiero, gdy symulator skończy ją zapisywać
    wynik["ostatnia_iteracja_kompletna"] = (
        odczyt.iteracja_kompletna(polaczenie, ostatnia, MAKS_PAR_NA_SWIECE) if ostatnia else False
    )
    return do_json(wynik)


@aplikacja.get("/api/iteracje")
def iteracje(limit: int = Query(50, ge=1, le=500), przed: Optional[int] = None,
             polaczenie: sqlite3.Connection = Depends(polaczenie_bazy)):
    return do_json(odczyt.lista_iteracji(polaczenie, limit, przed))


@aplikacja.get("/api/iteracje/{iteracja_id}")
def iteracja(iteracja_id: int, polaczenie: sqlite3.Connection = Depends(polaczenie_bazy)):
    wynik = odczyt.szczegoly_iteracji(polaczenie, iteracja_id)
    if wynik is None:
        raise HTTPException(404, "Nie ma takiej iteracji.")
    return do_json(wynik)


@aplikacja.get("/api/swiece")
def swiece(symbol: str, wokol: int, godzin_przed: int = Query(24, ge=1, le=200),
           interwal: str = INTERWAL):
    """Świece pary od `godzin_przed` przed chwilą `wokol` (ms) do teraz — do wykresu w raporcie."""
    od = pd.Timestamp(wokol, unit="ms", tz="UTC") - pd.Timedelta(hours=godzin_przed)
    tabela = pobierz_swiece_od(symbol, interwal, od, maks_swiec=500)
    tabela["czas"] = tabela["timestamp"].map(lambda t: int(t.timestamp()))  # sekundy (lightweight-charts)
    return do_json(tabela[["czas", "open", "high", "low", "close", "volume"]])


@aplikacja.get("/api/statystyki")
def statystyki(polaczenie: sqlite3.Connection = Depends(polaczenie_bazy)):
    rundy = baza.tabela_jako_df(polaczenie, "SELECT * FROM rundy ORDER BY czas_swiecy")
    pozycje = baza.tabela_jako_df(polaczenie, "SELECT * FROM pozycje WHERE status = 'zamknieta'")
    referencje = baza.tabela_jako_df(polaczenie, """
        SELECT oc.wynik_r, r.ma_sygnal_heurystyczny FROM oceny oc JOIN rundy r ON r.id = oc.runda_id
        WHERE oc.kto = 'referencja' AND oc.status = 'zamknieta'
    """)
    krzywa = odczyt.krzywa_kapitalu(polaczenie)
    try:
        btc, pary = kup_i_trzymaj_btc(rundy), kup_i_trzymaj_pary(rundy)
    except Exception:  # statystyki działają też bez dostępu do giełdy
        btc, pary = None, pd.DataFrame()
    return do_json({
        "lawa": statystyki_transakcji(pozycje["wynik_r"]) if not pozycje.empty else {"liczba": 0},
        "zawsze_wchodz": statystyki_transakcji(referencje["wynik_r"]),
        "heurystyka": statystyki_transakcji(referencje.loc[referencje["ma_sygnal_heurystyczny"] == 1, "wynik_r"]),
        "maks_spadek_procent": maks_spadek_procent(pd.Series([p["budzet"] for p in krzywa])),
        "krzywa_kapitalu": krzywa,
        "kup_i_trzymaj_btc": btc,
        "kup_i_trzymaj_pary": pary,
        "karta_traderow": karta_traderow(polaczenie),
        "trafnosc_wg_pewnosci": trafnosc_wg_pewnosci(polaczenie),
        "koszt_llm_dziennie": odczyt.koszt_llm_dziennie(polaczenie),
    })


@aplikacja.get("/api/lawa")
def lawa():
    konfiguracja = wczytaj_konfiguracje_lawy()
    return {
        "traderzy": [t.model_dump(include={"id", "nazwa", "aktywny", "fokus", "model", "zakres_danych"})
                     for t in konfiguracja.traderzy],
        "head_trader": konfiguracja.head_trader.model_dump(include={"nazwa", "model"}),
    }


# Zbudowany frontend — na końcu, żeby nie przykrywał ścieżek /api
if KATALOG_INTERFEJSU.exists():
    aplikacja.mount("/assets", StaticFiles(directory=KATALOG_INTERFEJSU / "assets"), name="assets")

    @aplikacja.get("/{sciezka:path}", include_in_schema=False)
    def frontend(sciezka: str):
        plik = KATALOG_INTERFEJSU / sciezka
        if sciezka and plik.is_file() and KATALOG_INTERFEJSU in plik.resolve().parents:
            return FileResponse(plik)
        return FileResponse(KATALOG_INTERFEJSU / "index.html")  # aplikacja jednostronicowa
