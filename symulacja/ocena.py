"""Rozstrzyganie transakcji (rzeczywistych i hipotetycznych) na podstawie zamkniętych świec.

Zasady konserwatywne — przy niepewności zakładamy gorszy wariant:
- luka w dół na otwarciu świecy poniżej SL → wyjście po cenie otwarcia (gorszej niż SL),
- luka w górę ponad TP → wyjście po TP (zlecenie limit nie da lepszej ceny),
- SL i TP w tej samej świecy → rozstrzygnięcie na świecach niższego interwału;
  gdy dalej nie wiadomo (albo brak rozstrzygającego) → SL."""
from dataclasses import dataclass
from typing import Callable, Optional

import pandas as pd


@dataclass
class WynikTransakcji:
    zamknieta: bool
    powod: Optional[str] = None  # TP / SL / CZAS
    czas_wyjscia: Optional[pd.Timestamp] = None
    cena_wyjscia: Optional[float] = None


# (czas otwarcia świecy, SL, TP) → "SL" | "TP" — kolejność trafienia wewnątrz świecy
Rozstrzygacz = Callable[[pd.Timestamp, float, float], str]


def _wyjscie_w_swiecy(swieca, stop_loss: float, take_profit: float,
                      rozstrzygnij: Optional[Rozstrzygacz]) -> Optional[tuple]:
    if swieca.open <= stop_loss:
        return "SL", float(swieca.open)
    if swieca.open >= take_profit:
        return "TP", take_profit
    sl_trafiony = swieca.low <= stop_loss
    tp_trafiony = swieca.high >= take_profit
    if sl_trafiony and tp_trafiony:
        kolejnosc = rozstrzygnij(swieca.timestamp, stop_loss, take_profit) if rozstrzygnij else "SL"
        return (kolejnosc, stop_loss) if kolejnosc == "SL" else ("TP", take_profit)
    if sl_trafiony:
        return "SL", stop_loss
    if tp_trafiony:
        return "TP", take_profit
    return None


def ocen_transakcje(swiece: pd.DataFrame, czas_wejscia: pd.Timestamp, stop_loss: float, take_profit: float,
                    maks_swiec: Optional[int] = None, rozstrzygnij: Optional[Rozstrzygacz] = None) -> WynikTransakcji:
    """Przechodzi świece od czasu wejścia i zwraca, co padło pierwsze: SL, TP albo limit czasu."""
    po_wejsciu = swiece[swiece["timestamp"] >= czas_wejscia]
    if maks_swiec is not None:
        po_wejsciu = po_wejsciu.head(maks_swiec)

    for swieca in po_wejsciu.itertuples(index=False):
        wyjscie = _wyjscie_w_swiecy(swieca, stop_loss, take_profit, rozstrzygnij)
        if wyjscie:
            powod, cena = wyjscie
            return WynikTransakcji(True, powod, swieca.timestamp, cena)

    if maks_swiec is not None and len(po_wejsciu) >= maks_swiec:
        ostatnia = po_wejsciu.iloc[-1]
        dlugosc = po_wejsciu["timestamp"].diff().dropna().min() if len(po_wejsciu) > 1 else pd.Timedelta(0)
        return WynikTransakcji(True, "CZAS", ostatnia["timestamp"] + dlugosc, float(ostatnia["close"]))
    return WynikTransakcji(False)


def kolejnosc_w_swiecach(swiece_nizsze: pd.DataFrame, stop_loss: float, take_profit: float) -> str:
    """Która granica padła pierwsza w świecach niższego interwału; remis w jednej świecy → SL."""
    for swieca in swiece_nizsze.itertuples(index=False):
        wyjscie = _wyjscie_w_swiecy(swieca, stop_loss, take_profit, rozstrzygnij=None)
        if wyjscie:
            return wyjscie[0]
    return "SL"


def wynik_netto(cena_wejscia: float, cena_wyjscia: float, stop_loss: float, koszt_procent: float) -> dict:
    """Wynik po kosztach w % pozycji i w jednostkach ryzyka R (R = strata przy SL z kosztami)."""
    wynik_procent = (cena_wyjscia / cena_wejscia - 1) * 100 - koszt_procent
    ryzyko_procent = (cena_wejscia - stop_loss) / cena_wejscia * 100 + koszt_procent
    return {"wynik_procent": wynik_procent, "wynik_r": wynik_procent / ryzyko_procent}
