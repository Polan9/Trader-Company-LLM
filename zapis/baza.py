"""Warstwa bazy danych (SQLite, tryb WAL) — jedyne miejsce, które zna silnik bazy.

Czasy zapisywane jako tekst ISO 8601 w UTC. Budżet nie jest przechowywany wprost:
aktualny budżet = budżet początkowy + suma wyników zamkniętych pozycji."""
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

_SCHEMAT = """
CREATE TABLE IF NOT EXISTS portfel (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    budzet_poczatkowy REAL NOT NULL,
    utworzono TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rundy (
    id INTEGER PRIMARY KEY,
    czas_utc TEXT NOT NULL,
    symbol TEXT NOT NULL,
    interwal TEXT NOT NULL,
    czas_swiecy TEXT NOT NULL,          -- otwarcie ostatniej zamkniętej świecy
    pominieta INTEGER NOT NULL,         -- 1 = ława nie zwołana (otwarta pozycja)
    cena_wejscia REAL,
    atr REAL,
    koszt_procent REAL,
    decyzja_lawy TEXT,                  -- TAK / NIE / NULL gdy pominięta
    otworz_pozycje INTEGER NOT NULL,
    powody TEXT,                        -- JSON lista
    ma_sygnal_heurystyczny INTEGER,
    koszt_llm_usd REAL NOT NULL DEFAULT 0,
    szczegoly TEXT,                     -- JSON: głosowanie, Head Trader, decyzja, analiza
    UNIQUE (symbol, interwal, czas_swiecy)
);
CREATE TABLE IF NOT EXISTS opinie (
    id INTEGER PRIMARY KEY,
    runda_id INTEGER NOT NULL REFERENCES rundy(id),
    trader_id TEXT NOT NULL,
    nazwa TEXT,
    model TEXT,
    glos TEXT NOT NULL,
    uzasadnienie TEXT,
    stop_loss REAL,
    take_profit REAL,
    skala_pozycji REAL,
    pewnosc REAL,                       -- 0–100, deklarowana przez tradera (NULL: starsze rundy / głos unieważniony)
    uwagi TEXT                          -- JSON lista
);
CREATE TABLE IF NOT EXISTS oceny (
    -- transakcje hipotetyczne: referencja (SL 1×ATR) i każda opinia TAK — do karty traderów
    id INTEGER PRIMARY KEY,
    runda_id INTEGER NOT NULL REFERENCES rundy(id),
    kto TEXT NOT NULL,                  -- 'referencja' albo id tradera
    symbol TEXT NOT NULL,
    interwal TEXT NOT NULL,
    czas_wejscia TEXT NOT NULL,
    cena_wejscia REAL NOT NULL,
    stop_loss REAL NOT NULL,
    take_profit REAL NOT NULL,
    koszt_procent REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'otwarta',
    powod TEXT,                         -- TP / SL / CZAS
    czas_wyjscia TEXT,
    cena_wyjscia REAL,
    wynik_procent REAL,                 -- netto, po kosztach
    wynik_r REAL
);
CREATE TABLE IF NOT EXISTS pozycje (
    id INTEGER PRIMARY KEY,
    runda_id INTEGER NOT NULL REFERENCES rundy(id),
    symbol TEXT NOT NULL,
    interwal TEXT NOT NULL,
    czas_wejscia TEXT NOT NULL,
    cena_wejscia REAL NOT NULL,
    stop_loss REAL NOT NULL,
    take_profit REAL NOT NULL,
    wielkosc_usd REAL NOT NULL,
    ryzyko_usd REAL NOT NULL,
    koszt_procent REAL NOT NULL,
    zrodlo_poziomow TEXT,
    status TEXT NOT NULL DEFAULT 'otwarta',
    powod TEXT,
    czas_wyjscia TEXT,
    cena_wyjscia REAL,
    wynik_usd REAL,
    wynik_procent REAL,
    wynik_r REAL
);
CREATE TABLE IF NOT EXISTS zuzycie_llm (
    id INTEGER PRIMARY KEY,
    runda_id INTEGER NOT NULL REFERENCES rundy(id),
    kto TEXT,
    model TEXT,
    tokeny_wejscie INTEGER,
    tokeny_wyjscie INTEGER,
    tokeny_rozumowanie INTEGER,
    koszt_usd REAL
);
CREATE INDEX IF NOT EXISTS ix_oceny_status ON oceny(status);
CREATE INDEX IF NOT EXISTS ix_pozycje_status ON pozycje(status, symbol);
"""


def _czas(wartosc: Optional[pd.Timestamp]) -> Optional[str]:
    return None if wartosc is None else pd.Timestamp(wartosc).tz_convert("UTC").isoformat()


def _json(wartosc: Any) -> str:
    return json.dumps(wartosc, ensure_ascii=False, default=str)


def polacz(sciezka: Path) -> sqlite3.Connection:
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    polaczenie = sqlite3.connect(sciezka)
    polaczenie.row_factory = sqlite3.Row
    polaczenie.execute("PRAGMA journal_mode=WAL")
    polaczenie.execute("PRAGMA foreign_keys=ON")
    return polaczenie


_MIGRACJE = [
    # (tabela, kolumna, definicja) — kolumny dodane po pierwszej wersji schematu
    ("opinie", "pewnosc", "REAL"),
]


def _migruj(polaczenie: sqlite3.Connection) -> None:
    """Dodaje brakujące kolumny w istniejącej bazie (CREATE TABLE IF NOT EXISTS nie zmienia tabel)."""
    for tabela, kolumna, definicja in _MIGRACJE:
        istniejace = {w["name"] for w in polaczenie.execute(f"PRAGMA table_info({tabela})")}
        if kolumna not in istniejace:
            polaczenie.execute(f"ALTER TABLE {tabela} ADD COLUMN {kolumna} {definicja}")


def inicjalizuj(polaczenie: sqlite3.Connection, budzet_poczatkowy: float) -> None:
    """Tworzy tabele i portfel (tylko przy pierwszym uruchomieniu — kolejne nie zmieniają budżetu)
    oraz dodaje kolumny z nowszych wersji schematu."""
    with polaczenie:
        polaczenie.executescript(_SCHEMAT)
        _migruj(polaczenie)
        polaczenie.execute(
            "INSERT OR IGNORE INTO portfel (id, budzet_poczatkowy, utworzono) VALUES (1, ?, ?)",
            (budzet_poczatkowy, _czas(pd.Timestamp.now(tz="UTC"))),
        )


# --- Portfel i liczniki ---

def budzet_poczatkowy(polaczenie: sqlite3.Connection) -> float:
    return float(polaczenie.execute("SELECT budzet_poczatkowy FROM portfel WHERE id = 1").fetchone()[0])


def aktualny_budzet(polaczenie: sqlite3.Connection) -> float:
    suma = polaczenie.execute(
        "SELECT COALESCE(SUM(wynik_usd), 0) FROM pozycje WHERE status = 'zamknieta'"
    ).fetchone()[0]
    return budzet_poczatkowy(polaczenie) + float(suma)


def liczniki_dzienne(polaczenie: sqlite3.Connection, dzien: pd.Timestamp) -> Dict[str, float]:
    """Dzienna strata (% aktualnego budżetu) i liczba otwartych dziś transakcji — doba UTC."""
    poczatek = _czas(dzien.tz_convert("UTC").normalize())
    koniec = _czas(dzien.tz_convert("UTC").normalize() + pd.Timedelta(days=1))
    wynik_dnia = polaczenie.execute(
        "SELECT COALESCE(SUM(wynik_usd), 0) FROM pozycje "
        "WHERE status = 'zamknieta' AND czas_wyjscia >= ? AND czas_wyjscia < ?",
        (poczatek, koniec),
    ).fetchone()[0]
    transakcje = polaczenie.execute(
        "SELECT COUNT(*) FROM pozycje WHERE czas_wejscia >= ? AND czas_wejscia < ?",
        (poczatek, koniec),
    ).fetchone()[0]
    budzet = aktualny_budzet(polaczenie)
    strata = max(0.0, -float(wynik_dnia)) / budzet * 100 if budzet > 0 else 100.0
    return {"dzienna_strata_procent": strata, "transakcje_dzisiaj": int(transakcje)}


# --- Rundy ---

def runda_istnieje(polaczenie: sqlite3.Connection, symbol: str, interwal: str, czas_swiecy: pd.Timestamp) -> bool:
    """Czy dla tej pary i świecy runda jest już zapisana."""
    return polaczenie.execute(
        "SELECT 1 FROM rundy WHERE symbol = ? AND interwal = ? AND czas_swiecy = ?",
        (symbol, interwal, _czas(czas_swiecy)),
    ).fetchone() is not None


def runda_dla_swiecy_istnieje(polaczenie: sqlite3.Connection, interwal: str, czas_swiecy: pd.Timestamp) -> bool:
    """Czy dla tej świecy była już runda (dowolna para — screener wybiera jedną parę na świecę)."""
    return polaczenie.execute(
        "SELECT 1 FROM rundy WHERE interwal = ? AND czas_swiecy = ?",
        (interwal, _czas(czas_swiecy)),
    ).fetchone() is not None


def zapisz_runde(polaczenie: sqlite3.Connection, **pola: Any) -> int:
    """Zapisuje rundę; pola JSON (powody, szczegoly) i czasy konwertowane automatycznie."""
    wiersz = {
        "czas_utc": _czas(pd.Timestamp.now(tz="UTC")),
        "pominieta": 0,
        "otworz_pozycje": 0,
        "koszt_llm_usd": 0.0,
        **pola,
    }
    wiersz["czas_swiecy"] = _czas(wiersz["czas_swiecy"])
    for pole in ("powody", "szczegoly"):
        if pole in wiersz:
            wiersz[pole] = _json(wiersz[pole])
    kolumny = ", ".join(wiersz)
    znaczniki = ", ".join("?" for _ in wiersz)
    kursor = polaczenie.execute(f"INSERT INTO rundy ({kolumny}) VALUES ({znaczniki})", tuple(wiersz.values()))
    return int(kursor.lastrowid)


def zapisz_opinie(polaczenie: sqlite3.Connection, runda_id: int, opinie: Dict[str, Dict[str, Any]]) -> None:
    polaczenie.executemany(
        "INSERT INTO opinie (runda_id, trader_id, nazwa, model, glos, uzasadnienie, stop_loss, "
        "take_profit, skala_pozycji, pewnosc, uwagi) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (runda_id, id_, o["nazwa"], o["model"], o["glos"], o["uzasadnienie"], o["stop_loss"],
             o["take_profit"], o["wielkosc_pozycji_procent"], o.get("pewnosc"), _json(o["uwagi"]))
            for id_, o in opinie.items()
        ],
    )


def zapisz_zuzycie(polaczenie: sqlite3.Connection, runda_id: int, zuzycie: List[Dict[str, Any]]) -> None:
    polaczenie.executemany(
        "INSERT INTO zuzycie_llm (runda_id, kto, model, tokeny_wejscie, tokeny_wyjscie, "
        "tokeny_rozumowanie, koszt_usd) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (runda_id, w["kto"], w["model"], w["tokeny_wejscie"], w["tokeny_wyjscie"],
             w["tokeny_rozumowanie"], w["koszt_usd"])
            for w in zuzycie
        ],
    )


# --- Oceny (transakcje hipotetyczne) i pozycje ---

def zapisz_ocene(polaczenie: sqlite3.Connection, runda_id: int, kto: str, symbol: str, interwal: str,
                 czas_wejscia: pd.Timestamp, cena_wejscia: float, stop_loss: float, take_profit: float,
                 koszt_procent: float) -> int:
    kursor = polaczenie.execute(
        "INSERT INTO oceny (runda_id, kto, symbol, interwal, czas_wejscia, cena_wejscia, stop_loss, "
        "take_profit, koszt_procent) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (runda_id, kto, symbol, interwal, _czas(czas_wejscia), cena_wejscia, stop_loss, take_profit, koszt_procent),
    )
    return int(kursor.lastrowid)


def zapisz_pozycje(polaczenie: sqlite3.Connection, runda_id: int, symbol: str, interwal: str,
                   czas_wejscia: pd.Timestamp, decyzja: Dict[str, Any]) -> int:
    kursor = polaczenie.execute(
        "INSERT INTO pozycje (runda_id, symbol, interwal, czas_wejscia, cena_wejscia, stop_loss, take_profit, "
        "wielkosc_usd, ryzyko_usd, koszt_procent, zrodlo_poziomow) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (runda_id, symbol, interwal, _czas(czas_wejscia), decyzja["cena_wejscia"], decyzja["stop_loss"],
         decyzja["take_profit"], decyzja["wielkosc_usd"], decyzja["ryzyko_usd"], decyzja["koszt_procent"],
         decyzja.get("zrodlo_poziomow")),
    )
    return int(kursor.lastrowid)


def otwarte(polaczenie: sqlite3.Connection, tabela: str) -> List[sqlite3.Row]:
    """Otwarte pozycje albo nierozstrzygnięte oceny (`tabela`: 'pozycje' | 'oceny')."""
    if tabela not in ("pozycje", "oceny"):
        raise ValueError(f"Nieznana tabela: {tabela}")
    return polaczenie.execute(f"SELECT * FROM {tabela} WHERE status = 'otwarta'").fetchall()


def zamknij(polaczenie: sqlite3.Connection, tabela: str, id_: int, **wynik: Any) -> None:
    """Zamyka pozycję lub ocenę: powod, czas_wyjscia, cena_wyjscia, wynik_procent, wynik_r (+ wynik_usd)."""
    if tabela not in ("pozycje", "oceny"):
        raise ValueError(f"Nieznana tabela: {tabela}")
    wynik["czas_wyjscia"] = _czas(wynik["czas_wyjscia"])
    przypisania = ", ".join(f"{kolumna} = ?" for kolumna in wynik)
    polaczenie.execute(
        f"UPDATE {tabela} SET status = 'zamknieta', {przypisania} WHERE id = ?", (*wynik.values(), id_)
    )


# --- Odczyty do raportu ---

def tabela_jako_df(polaczenie: sqlite3.Connection, zapytanie: str, parametry: tuple = ()) -> pd.DataFrame:
    return pd.read_sql_query(zapytanie, polaczenie, params=parametry)
