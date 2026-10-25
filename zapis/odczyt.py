"""Odczyty dla interfejsu (API) — tylko do odczytu, połączenie otwierane w trybie `mode=ro`,
więc interfejs fizycznie nie może zmienić danych symulatora.

Iteracja = wszystkie rundy jednej świecy (screener + kolejne pary z przeszukiwania).
Identyfikator iteracji w API: czas świecy w milisekundach (bez znaków problematycznych w URL)."""
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from zapis import baza


def polacz_do_odczytu(sciezka: Path) -> sqlite3.Connection:
    polaczenie = sqlite3.connect(f"file:{sciezka.as_posix()}?mode=ro", uri=True, check_same_thread=False)
    polaczenie.row_factory = sqlite3.Row
    return polaczenie


def czas_na_ms(czas_iso: str) -> int:
    return int(pd.Timestamp(czas_iso).timestamp() * 1000)


def ms_na_czas(ms: int) -> str:
    return pd.Timestamp(ms, unit="ms", tz="UTC").isoformat()


def _json_lub_pusty(tekst: Optional[str], domyslnie: Any) -> Any:
    return json.loads(tekst) if tekst else domyslnie


def stan_portfela(polaczenie: sqlite3.Connection) -> Dict[str, Any]:
    """Budżet, koszt LLM, otwarte pozycje i czas ostatniej iteracji."""
    start = baza.budzet_poczatkowy(polaczenie)
    budzet = baza.aktualny_budzet(polaczenie)
    podsumowanie = polaczenie.execute(
        "SELECT COUNT(*) AS rundy, COALESCE(SUM(koszt_llm_usd), 0) AS koszt, MAX(czas_swiecy) AS ostatnia "
        "FROM rundy"
    ).fetchone()
    zamkniete = polaczenie.execute(
        "SELECT COUNT(*) AS liczba, COALESCE(SUM(wynik_usd > 0), 0) AS wygrane FROM pozycje WHERE status = 'zamknieta'"
    ).fetchone()
    return {
        "budzet_poczatkowy": start,
        "budzet": budzet,
        "wynik_procent": (budzet / start - 1) * 100 if start else 0.0,
        "koszt_llm_usd": float(podsumowanie["koszt"]),
        "liczba_rund": int(podsumowanie["rundy"]),
        "ostatnia_swieca": podsumowanie["ostatnia"],
        "ostatnia_iteracja_ms": czas_na_ms(podsumowanie["ostatnia"]) if podsumowanie["ostatnia"] else None,
        "zamkniete_pozycje": int(zamkniete["liczba"]),
        "wygrane_pozycje": int(zamkniete["wygrane"]),
        "otwarte_pozycje": [dict(w) for w in baza.otwarte(polaczenie, "pozycje")],
    }


def lista_iteracji(polaczenie: sqlite3.Connection, limit: int = 50,
                   przed_ms: Optional[int] = None) -> List[Dict[str, Any]]:
    """Ostatnie iteracje (najnowsze pierwsze) ze skrótem każdej rundy."""
    warunek, parametry = "", []
    if przed_ms is not None:
        warunek, parametry = "WHERE czas_swiecy < ?", [ms_na_czas(przed_ms)]
    czasy = [w[0] for w in polaczenie.execute(
        f"SELECT DISTINCT czas_swiecy FROM rundy {warunek} ORDER BY czas_swiecy DESC LIMIT ?",
        (*parametry, limit),
    )]
    if not czasy:
        return []
    znaczniki = ", ".join("?" for _ in czasy)
    rundy = polaczenie.execute(
        f"SELECT id, czas_swiecy, symbol, pominieta, decyzja_lawy, otworz_pozycje, powody, koszt_llm_usd, szczegoly "
        f"FROM rundy WHERE czas_swiecy IN ({znaczniki}) ORDER BY id",
        czasy,
    ).fetchall()

    iteracje: Dict[str, Dict[str, Any]] = {
        czas: {"id": czas_na_ms(czas), "czas_swiecy": czas, "rundy": [], "koszt_llm_usd": 0.0} for czas in czasy
    }
    for runda in rundy:
        szczegoly = _json_lub_pusty(runda["szczegoly"], {})
        glosowanie = szczegoly.get("wynik_glosowania") or {}
        iteracja = iteracje[runda["czas_swiecy"]]
        iteracja["koszt_llm_usd"] += runda["koszt_llm_usd"] or 0.0
        iteracja["rundy"].append({
            "id": runda["id"],
            "symbol": runda["symbol"],
            "pominieta": bool(runda["pominieta"]),
            "decyzja": runda["decyzja_lawy"],
            "tak": glosowanie.get("tak"),
            "nie": glosowanie.get("nie"),
            "otworz_pozycje": bool(runda["otworz_pozycje"]),
            "powody": _json_lub_pusty(runda["powody"], []),
        })
    return [iteracje[czas] for czas in czasy]


def szczegoly_iteracji(polaczenie: sqlite3.Connection, iteracja_ms: int) -> Optional[Dict[str, Any]]:
    """Pełna iteracja: ranking screenera i każda runda z analizą, opiniami, ocenami i zużyciem LLM."""
    czas = ms_na_czas(iteracja_ms)
    rundy = polaczenie.execute("SELECT * FROM rundy WHERE czas_swiecy = ? ORDER BY id", (czas,)).fetchall()
    if not rundy:
        return None

    wynik_rund = []
    screener = None
    for runda in rundy:
        szczegoly = _json_lub_pusty(runda["szczegoly"], {})
        screener = screener or szczegoly.get("screener")
        opinie = [
            {**dict(o), "uwagi": _json_lub_pusty(o["uwagi"], [])}
            for o in polaczenie.execute("SELECT * FROM opinie WHERE runda_id = ? ORDER BY id", (runda["id"],))
        ]
        oceny = [dict(o) for o in polaczenie.execute("SELECT * FROM oceny WHERE runda_id = ? ORDER BY id", (runda["id"],))]
        zuzycie = [dict(z) for z in polaczenie.execute("SELECT * FROM zuzycie_llm WHERE runda_id = ?", (runda["id"],))]
        pozycja = polaczenie.execute("SELECT * FROM pozycje WHERE runda_id = ?", (runda["id"],)).fetchone()
        wynik_rund.append({
            "id": runda["id"],
            "symbol": runda["symbol"],
            "interwal": runda["interwal"],
            "pominieta": bool(runda["pominieta"]),
            "cena_wejscia": runda["cena_wejscia"],
            "atr": runda["atr"],
            "koszt_procent": runda["koszt_procent"],
            "decyzja": runda["decyzja_lawy"],
            "otworz_pozycje": bool(runda["otworz_pozycje"]),
            "powody": _json_lub_pusty(runda["powody"], []),
            "koszt_llm_usd": runda["koszt_llm_usd"],
            "glosowanie": szczegoly.get("wynik_glosowania"),
            "head_trader": szczegoly.get("decyzja_head_tradera"),
            "decyzja_koncowa": szczegoly.get("decyzja_koncowa"),
            "ticker": szczegoly.get("aktualne_dane"),
            "analiza": szczegoly.get("analiza_techniczna"),
            "opinie": opinie,
            "oceny": oceny,
            "zuzycie": zuzycie,
            "pozycja": dict(pozycja) if pozycja else None,
        })
    return {
        "id": iteracja_ms,
        "czas_swiecy": czas,
        "koszt_llm_usd": sum(r["koszt_llm_usd"] or 0.0 for r in wynik_rund),
        "screener": screener,
        "rundy": wynik_rund,
    }


def koszt_llm_dziennie(polaczenie: sqlite3.Connection) -> List[Dict[str, Any]]:
    return [dict(w) for w in polaczenie.execute(
        "SELECT substr(czas_swiecy, 1, 10) AS dzien, SUM(koszt_llm_usd) AS koszt_usd, COUNT(*) AS rundy "
        "FROM rundy GROUP BY dzien ORDER BY dzien"
    )]


def krzywa_kapitalu(polaczenie: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Budżet po każdej zamkniętej pozycji (punkt startowy = budżet początkowy)."""
    budzet = baza.budzet_poczatkowy(polaczenie)
    punkty = [{"czas": None, "budzet": budzet}]
    for w in polaczenie.execute(
        "SELECT czas_wyjscia, wynik_usd FROM pozycje WHERE status = 'zamknieta' ORDER BY czas_wyjscia"
    ):
        budzet += w["wynik_usd"]
        punkty.append({"czas": w["czas_wyjscia"], "budzet": budzet})
    return punkty
