"""Jedno miejsce wywołań LLM — klienci tworzeni leniwie i współdzieleni między węzłami.

Każde wywołanie zapisuje zużycie tokenów do rejestru, z którego liczony jest koszt rundy."""
import threading
from functools import lru_cache
from typing import Any, Dict, List, Optional, Type, TypeVar

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from konfiguracja.lawa import KonfiguracjaModelu
from konfiguracja.ustawienia import CENNIK_MODELI

Schemat = TypeVar("Schemat", bound=BaseModel)

_rejestr_zuzycia: List[Dict[str, Any]] = []
_blokada_rejestru = threading.Lock()  # traderzy wołają modele równolegle


@lru_cache(maxsize=None)
def _klient(model: str, temperatura: Optional[float], reasoning_effort: Optional[str]) -> ChatOpenAI:
    # Parametry przekazywane tylko gdy ustawione — modele rozumujące nie wspierają temperature
    parametry = {"model": model}
    if temperatura is not None:
        parametry["temperature"] = temperatura
    if reasoning_effort is not None:
        parametry["reasoning_effort"] = reasoning_effort
    return ChatOpenAI(**parametry)


def _koszt_usd(model: str, wejscie: int, z_cache: int, wyjscie: int) -> Optional[float]:
    if model not in CENNIK_MODELI:
        return None
    cena_wejscia, cena_cache, cena_wyjscia = CENNIK_MODELI[model]
    return ((wejscie - z_cache) * cena_wejscia + z_cache * cena_cache + wyjscie * cena_wyjscia) / 1_000_000


def _zapisz_zuzycie(kto: str, model: str, odpowiedz: Any) -> None:
    uzycie = getattr(odpowiedz, "usage_metadata", None) or {}
    wejscie = uzycie.get("input_tokens", 0)
    wyjscie = uzycie.get("output_tokens", 0)  # zawiera tokeny rozumowania
    z_cache = (uzycie.get("input_token_details") or {}).get("cache_read", 0) or 0
    rozumowanie = (uzycie.get("output_token_details") or {}).get("reasoning", 0) or 0
    with _blokada_rejestru:
        _rejestr_zuzycia.append({
            "kto": kto,
            "model": model,
            "tokeny_wejscie": wejscie,
            "tokeny_wyjscie": wyjscie,
            "tokeny_rozumowanie": rozumowanie,
            "koszt_usd": _koszt_usd(model, wejscie, z_cache, wyjscie),
        })


def zapytaj_model(
    konfiguracja: KonfiguracjaModelu, schemat: Type[Schemat], wiadomosci: List[BaseMessage], kto: str = ""
) -> Schemat:
    klient = _klient(konfiguracja.model, konfiguracja.temperatura, konfiguracja.reasoning_effort)
    wynik = klient.with_structured_output(schemat, include_raw=True).invoke(wiadomosci)
    _zapisz_zuzycie(kto or konfiguracja.model, konfiguracja.model, wynik["raw"])
    if wynik["parsing_error"] is not None:
        raise wynik["parsing_error"]
    return wynik["parsed"]


def pobierz_i_wyczysc_zuzycie() -> List[Dict[str, Any]]:
    with _blokada_rejestru:
        zuzycie = list(_rejestr_zuzycia)
        _rejestr_zuzycia.clear()
    return zuzycie
