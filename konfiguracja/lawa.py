"""Wczytywanie konfiguracji ławy (role, osobowości, modele, zakres danych) z pliku JSON.

Konfiguracja to dane, nie kod — docelowo edytowana z UI."""
import json
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field

from konfiguracja.ustawienia import PLIK_KONFIGURACJI_LAWY


class KonfiguracjaModelu(BaseModel):
    model: str
    temperatura: Optional[float] = None
    reasoning_effort: Optional[str] = None


class KonfiguracjaTradera(KonfiguracjaModelu):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")  # używane jako nazwa węzła grafu
    nazwa: str
    aktywny: bool = True
    osobowosc: str
    fokus: str
    zakres_danych: List[str]


class KonfiguracjaHeadTradera(KonfiguracjaModelu):
    nazwa: str
    osobowosc: str


class KonfiguracjaLawy(BaseModel):
    traderzy: List[KonfiguracjaTradera]
    head_trader: KonfiguracjaHeadTradera

    @property
    def aktywni_traderzy(self) -> List[KonfiguracjaTradera]:
        return [trader for trader in self.traderzy if trader.aktywny]


def wczytaj_konfiguracje_lawy(sciezka: Path = PLIK_KONFIGURACJI_LAWY) -> KonfiguracjaLawy:
    with open(sciezka, encoding="utf-8") as plik:
        konfiguracja = KonfiguracjaLawy.model_validate(json.load(plik))

    identyfikatory = [trader.id for trader in konfiguracja.traderzy]
    if len(identyfikatory) != len(set(identyfikatory)):
        raise ValueError(f"Powtórzone id traderów w {sciezka.name}: {identyfikatory}")
    if not konfiguracja.aktywni_traderzy:
        raise ValueError(f"Brak aktywnych traderów w {sciezka.name}.")
    return konfiguracja
