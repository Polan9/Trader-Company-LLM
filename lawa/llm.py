"""Jedno miejsce wywołań LLM — klienci tworzeni leniwie i współdzieleni między węzłami."""
from functools import lru_cache
from typing import List, Optional, Type, TypeVar

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from konfiguracja.lawa import KonfiguracjaModelu

Schemat = TypeVar("Schemat", bound=BaseModel)


@lru_cache(maxsize=None)
def _klient(model: str, temperatura: Optional[float], reasoning_effort: Optional[str]) -> ChatOpenAI:
    # Parametry przekazywane tylko gdy ustawione — modele rozumujące nie wspierają temperature
    parametry = {"model": model}
    if temperatura is not None:
        parametry["temperature"] = temperatura
    if reasoning_effort is not None:
        parametry["reasoning_effort"] = reasoning_effort
    return ChatOpenAI(**parametry)


def zapytaj_model(
    konfiguracja: KonfiguracjaModelu, schemat: Type[Schemat], wiadomosci: List[BaseMessage]
) -> Schemat:
    klient = _klient(konfiguracja.model, konfiguracja.temperatura, konfiguracja.reasoning_effort)
    return klient.with_structured_output(schemat).invoke(wiadomosci)
