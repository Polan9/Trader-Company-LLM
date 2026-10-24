"""Ustrukturyzowane odpowiedzi LLM (pydantic) — zamiast parsowania tekstu."""
from typing import Literal, Optional

from pydantic import BaseModel, Field


class OpiniaTradera(BaseModel):
    glos: Literal["TAK", "NIE"] = Field(
        description="TAK = otworzyć teraz pozycję long (kupno spot), NIE = nie otwierać."
    )
    uzasadnienie: str = Field(description="Zwięzłe uzasadnienie decyzji (2–5 zdań).")
    stop_loss: Optional[float] = Field(
        description="Cena stop-loss poniżej ceny wejścia. Wymagana przy TAK, przy NIE null."
    )
    take_profit: Optional[float] = Field(
        description="Cena take-profit powyżej ceny wejścia. Wymagana przy TAK, przy NIE null."
    )
    wielkosc_pozycji_procent: Optional[float] = Field(
        description=(
            "Skala pełnej pozycji w procentach (0–100), NIE procent budżetu. Pełną pozycję wylicza "
            "Risk Manager z ryzyka i limitów: 100 = pełna pozycja (pełne przekonanie), "
            "50 = połowa, 25 = ćwierć. Przy NIE null."
        )
    )


class DecyzjaHeadTradera(BaseModel):
    stop_loss: float = Field(description="Wybrana cena stop-loss (z zakresu propozycji traderów).")
    take_profit: float = Field(description="Wybrana cena take-profit (z zakresu propozycji traderów).")
    uzasadnienie: str = Field(description="Dlaczego te poziomy (2–5 zdań), z odniesieniem do argumentów ławy.")
