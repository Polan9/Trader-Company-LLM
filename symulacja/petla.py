"""Pętla symulatora: co interwał (po zamknięciu świecy) rozlicza otwarte transakcje
i — jeśli nie ma otwartej pozycji — zwołuje ławę. Stan w SQLite, więc restart jest bezpieczny:
rundy są unikalne per świeca, a otwarte pozycje i oceny są dokańczane po wznowieniu."""
import logging
import sqlite3
import time
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Optional

import ccxt
import pandas as pd

from dane.gielda import cena_wejscia, pobierz_swiece_od
from konfiguracja.ustawienia import (
    INTERWAL_ROZSTRZYGANIA,
    KATALOG_LOGOW,
    MAKS_CZAS_POZYCJI_SWIEC,
    MAKS_OTWARTYCH_POZYCJI,
    OPOZNIENIE_PO_ZAMKNIECIU_S,
    PROBY_CYKLU,
    PRZERWA_PO_BLEDZIE_S,
    REFERENCJA_SL_ATR,
    SCREENER_WLACZONY,
)
from lawa.llm import pobierz_i_wyczysc_zuzycie
from lawa.sl_tp import koszt_transakcji_procent, minimalny_take_profit
from screener.wybor import formatuj_ranking, wybierz_pare
from symulacja.ocena import kolejnosc_w_swiecach, ocen_transakcje, wynik_netto
from zapis import baza
from zapis.plik_stanu import zapisz_stan

log = logging.getLogger("symulacja")

BRAK_PARY = "BRAK"  # symbol rundy pominiętej, gdy screener nic nie wybrał


def skonfiguruj_logi() -> None:
    KATALOG_LOGOW.mkdir(parents=True, exist_ok=True)
    format_ = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    plik = RotatingFileHandler(KATALOG_LOGOW / "symulacja.log", maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    plik.setFormatter(format_)
    konsola = logging.StreamHandler()
    konsola.setFormatter(format_)
    log.setLevel(logging.INFO)
    log.handlers = [plik, konsola]


def dlugosc_swiecy(interwal: str) -> pd.Timedelta:
    return pd.Timedelta(seconds=ccxt.Exchange.parse_timeframe(interwal))


def ostatnia_zamknieta_swieca(teraz: pd.Timestamp, interwal: str) -> pd.Timestamp:
    """Czas otwarcia ostatniej zamkniętej świecy wg zegara (bez pytania giełdy)."""
    dlugosc = dlugosc_swiecy(interwal)
    return teraz.floor(dlugosc) - dlugosc


def sekundy_do_nastepnej_rundy(teraz: pd.Timestamp, interwal: str) -> float:
    dlugosc = dlugosc_swiecy(interwal)
    nastepne_zamkniecie = teraz.floor(dlugosc) + dlugosc
    return (nastepne_zamkniecie - teraz).total_seconds() + OPOZNIENIE_PO_ZAMKNIECIU_S


# --- Rozliczanie otwartych pozycji i ocen ---

def _rozstrzygacz(symbol: str, interwal: str):
    def rozstrzygnij(czas_swiecy: pd.Timestamp, stop_loss: float, take_profit: float) -> str:
        liczba = int(dlugosc_swiecy(interwal) / dlugosc_swiecy(INTERWAL_ROZSTRZYGANIA))
        nizsze = pobierz_swiece_od(symbol, INTERWAL_ROZSTRZYGANIA, czas_swiecy, maks_swiec=liczba)
        nizsze = nizsze[nizsze["timestamp"] < czas_swiecy + dlugosc_swiecy(interwal)]
        return kolejnosc_w_swiecach(nizsze, stop_loss, take_profit)
    return rozstrzygnij


def rozlicz_otwarte(polaczenie: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Sprawdza na nowych świecach, czy otwarte pozycje/oceny trafiły SL, TP albo limit czasu."""
    zamkniete = []
    wiersze = [("pozycje", w) for w in baza.otwarte(polaczenie, "pozycje")]
    wiersze += [("oceny", w) for w in baza.otwarte(polaczenie, "oceny")]
    if not wiersze:
        return zamkniete

    grupy: Dict[tuple, list] = {}
    for tabela, wiersz in wiersze:
        grupy.setdefault((wiersz["symbol"], wiersz["interwal"]), []).append((tabela, wiersz))

    for (symbol, interwal), elementy in grupy.items():
        najstarsze = min(pd.Timestamp(w["czas_wejscia"]) for _, w in elementy)
        swiece = pobierz_swiece_od(symbol, interwal, najstarsze)
        rozstrzygnij = _rozstrzygacz(symbol, interwal)
        with polaczenie:
            for tabela, wiersz in elementy:
                wynik = ocen_transakcje(
                    swiece, pd.Timestamp(wiersz["czas_wejscia"]), wiersz["stop_loss"], wiersz["take_profit"],
                    MAKS_CZAS_POZYCJI_SWIEC, rozstrzygnij,
                )
                if not wynik.zamknieta:
                    continue
                netto = wynik_netto(wiersz["cena_wejscia"], wynik.cena_wyjscia, wiersz["stop_loss"], wiersz["koszt_procent"])
                pola = {"powod": wynik.powod, "czas_wyjscia": wynik.czas_wyjscia, "cena_wyjscia": wynik.cena_wyjscia, **netto}
                if tabela == "pozycje":
                    pola["wynik_usd"] = wiersz["wielkosc_usd"] * netto["wynik_procent"] / 100
                baza.zamknij(polaczenie, tabela, wiersz["id"], **pola)
                zamkniete.append({"tabela": tabela, "id": wiersz["id"], **pola})
                if tabela == "pozycje":
                    log.info(f"Pozycja #{wiersz['id']} {symbol} zamknięta: {wynik.powod} "
                             f"{pola['wynik_usd']:+.2f} USD ({netto['wynik_r']:+.2f} R)")
    return zamkniete


# --- Runda ławy ---

def _skrot_screenera(wynik_screenera: Dict[str, Any], liczba: int = 10) -> Dict[str, Any]:
    """Do zapisu w bazie: wybrana para, czołówka rankingu i powody odrzuceń."""
    return {
        "symbol": wynik_screenera["symbol"],
        "ranking": wynik_screenera["ranking"][:liczba],
        "odrzucone": [{"symbol": o["symbol"], "odrzucenia": o["odrzucenia"]} for o in wynik_screenera["odrzucone"]],
    }


def _zapisz_wynik_rundy(polaczenie: sqlite3.Connection, wynik: Dict[str, Any], zuzycie: List[Dict[str, Any]],
                        czas_swiecy: pd.Timestamp, wynik_screenera: Optional[Dict[str, Any]] = None) -> int:
    symbol, interwal = wynik["symbol"], wynik["interwal"]
    analiza = wynik["analiza_techniczna"]
    decyzja = wynik["decyzja_koncowa"]
    cena = cena_wejscia(wynik["aktualne_dane"])
    atr = analiza["atr"]["wartosc"]
    koszt = koszt_transakcji_procent(wynik["aktualne_dane"].get("spread_procent"))
    czas_wejscia = czas_swiecy + dlugosc_swiecy(interwal)  # wejście w świecy po decyzji

    with polaczenie:
        runda_id = baza.zapisz_runde(
            polaczenie, symbol=symbol, interwal=interwal, czas_swiecy=czas_swiecy,
            cena_wejscia=cena, atr=atr, koszt_procent=koszt,
            decyzja_lawy=wynik["wynik_glosowania"]["decyzja"],
            otworz_pozycje=int(bool(decyzja.get("otworz_pozycje"))),
            powody=decyzja.get("powody", []),
            ma_sygnal_heurystyczny=int(analiza["moment_wejscia_wyjscia"]["ma_sygnal_wejscia"]),
            koszt_llm_usd=sum(w["koszt_usd"] or 0 for w in zuzycie),
            szczegoly={
                "wynik_glosowania": wynik["wynik_glosowania"],
                "decyzja_head_tradera": wynik["decyzja_head_tradera"],
                "decyzja_koncowa": decyzja,
                "aktualne_dane": wynik["aktualne_dane"],
                "analiza_techniczna": analiza,
                "screener": _skrot_screenera(wynik_screenera) if wynik_screenera else None,
            },
        )
        baza.zapisz_opinie(polaczenie, runda_id, wynik["opinie"])
        baza.zapisz_zuzycie(polaczenie, runda_id, zuzycie)

        # Transakcja referencyjna — miara dla głosów NIE i strategia odniesienia w raporcie
        sl_ref = cena - REFERENCJA_SL_ATR * atr
        baza.zapisz_ocene(polaczenie, runda_id, "referencja", symbol, interwal, czas_wejscia,
                          cena, sl_ref, minimalny_take_profit(cena, sl_ref, koszt), koszt)
        # Każdy ważny głos TAK oceniany na własnych poziomach tradera
        for trader_id, opinia in wynik["opinie"].items():
            if opinia["glos"] == "TAK":
                baza.zapisz_ocene(polaczenie, runda_id, trader_id, symbol, interwal, czas_wejscia,
                                  cena, opinia["stop_loss"], opinia["take_profit"], koszt)

        if decyzja.get("otworz_pozycje"):
            pozycja_id = baza.zapisz_pozycje(polaczenie, runda_id, symbol, interwal, czas_wejscia, decyzja)
            log.info(f"Otwarta pozycja #{pozycja_id} {symbol}: {decyzja['wielkosc_usd']:.2f} USD @ {cena:.8g} "
                     f"SL {decyzja['stop_loss']:.8g} TP {decyzja['take_profit']:.8g}")
    return runda_id


def wykonaj_cykl(polaczenie: sqlite3.Connection, graf, stan_poczatkowy: Dict[str, Any],
                 teraz: pd.Timestamp = None) -> Dict[str, Any]:
    """Jeden cykl: rozliczenie otwartych → screener → (ewentualnie) runda ławy → zapis."""
    teraz = teraz or pd.Timestamp.now(tz="UTC")
    interwal = stan_poczatkowy["interwal"]
    czas_swiecy = ostatnia_zamknieta_swieca(teraz, interwal)

    rozlicz_otwarte(polaczenie)

    if baza.runda_dla_swiecy_istnieje(polaczenie, interwal, czas_swiecy):
        log.info(f"Runda dla świecy {czas_swiecy} już jest w bazie — pomijam.")
        return {"status": "juz_byla", "czas_swiecy": czas_swiecy}

    otwarte_pozycje = baza.otwarte(polaczenie, "pozycje")
    if len(otwarte_pozycje) >= MAKS_OTWARTYCH_POZYCJI:
        numery = ", ".join(f"#{p['id']} {p['symbol']}" for p in otwarte_pozycje)
        with polaczenie:
            baza.zapisz_runde(polaczenie, symbol=otwarte_pozycje[0]["symbol"], interwal=interwal,
                              czas_swiecy=czas_swiecy, pominieta=1, powody=[f"otwarte pozycje: {numery}"])
        log.info(f"Limit otwartych pozycji ({numery}) — ława nie jest zwoływana.")
        return {"status": "pominieta", "czas_swiecy": czas_swiecy}

    wynik_screenera = None
    symbol = stan_poczatkowy["symbol"]
    if SCREENER_WLACZONY:
        wynik_screenera = wybierz_pare(interwal, pomin={p["symbol"] for p in otwarte_pozycje})
        log.info(formatuj_ranking(wynik_screenera, liczba=5))
        if wynik_screenera["symbol"] is None:
            with polaczenie:
                baza.zapisz_runde(polaczenie, symbol=BRAK_PARY, interwal=interwal, czas_swiecy=czas_swiecy,
                                  pominieta=1, powody=["screener: żadna para nie spełnia kryteriów"],
                                  szczegoly={"screener": _skrot_screenera(wynik_screenera)})
            return {"status": "brak_pary", "czas_swiecy": czas_swiecy}
        symbol = wynik_screenera["symbol"]

    stan = {
        **stan_poczatkowy,
        "symbol": symbol,
        "budzet": baza.aktualny_budzet(polaczenie),
        **baza.liczniki_dzienne(polaczenie, teraz),
    }
    pobierz_i_wyczysc_zuzycie()  # rejestr tylko dla tej rundy
    wynik = graf.invoke(stan)
    zuzycie = pobierz_i_wyczysc_zuzycie()

    czas_z_danych = pd.Timestamp(wynik["analiza_techniczna"]["czas_ostatniej_swiecy"])
    if czas_z_danych != czas_swiecy:
        log.warning(f"Giełda zwróciła świecę {czas_z_danych} zamiast {czas_swiecy} — zapisuję pod czasem z danych.")
        if baza.runda_dla_swiecy_istnieje(polaczenie, interwal, czas_z_danych):
            return {"status": "juz_byla", "czas_swiecy": czas_z_danych}

    runda_id = _zapisz_wynik_rundy(polaczenie, wynik, zuzycie, czas_z_danych, wynik_screenera)
    zapisz_stan(wynik, zuzycie)
    glosowanie = wynik["wynik_glosowania"]
    log.info(f"Runda #{runda_id} {symbol} ({czas_z_danych}): {glosowanie['tak']} TAK / {glosowanie['nie']} NIE, "
             f"otwarcie: {wynik['decyzja_koncowa'].get('otworz_pozycje')}, "
             f"koszt LLM ${sum(w['koszt_usd'] or 0 for w in zuzycie):.4f}")
    return {"status": "runda", "runda_id": runda_id, "czas_swiecy": czas_z_danych}


def uruchom(polaczenie: sqlite3.Connection, graf, stan_poczatkowy: Dict[str, Any], raz: bool = False) -> None:
    """Główna pętla. `raz=True` — jeden cykl i koniec (np. do testów albo timera systemd)."""
    while True:
        for proba in range(1, PROBY_CYKLU + 1):
            try:
                wykonaj_cykl(polaczenie, graf, stan_poczatkowy)
                break
            except Exception:
                log.exception(f"Błąd cyklu (próba {proba}/{PROBY_CYKLU})")
                if proba < PROBY_CYKLU:
                    time.sleep(PRZERWA_PO_BLEDZIE_S)
        if raz:
            return
        czekaj = sekundy_do_nastepnej_rundy(pd.Timestamp.now(tz="UTC"), stan_poczatkowy["interwal"])
        log.info(f"Następna runda za {czekaj / 60:.1f} min.")
        time.sleep(czekaj)
