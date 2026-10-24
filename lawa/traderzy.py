"""Fabryka węzłów-traderów: jeden trader = jedna konfiguracja z konfiguracja/lawa.json."""
from typing import Any, Callable, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from dane.gielda import cena_wejscia
from konfiguracja.lawa import KonfiguracjaTradera
from lawa import llm
from lawa.bloki_danych import sprawdz_zakres_danych, zloz_dane
from lawa.modele import OpiniaTradera
from lawa.sl_tp import koszt_transakcji_procent, opis_regul, sprawdz_sl_tp
from stan import AktualnyStan


def _prompt_systemowy(trader: KonfiguracjaTradera) -> str:
    return f"""
    {trader.osobowosc}

    Twoja rola w ławie traderów: {trader.nazwa}.
    Twoja specjalizacja: {trader.fokus}.

    Ława kilku traderów niezależnie głosuje, czy otworzyć teraz pozycję long (kupno spot).
    Nie widzisz głosów innych — oceniasz wyłącznie z perspektywy swojej specjalizacji
    i tylko na podstawie danych, które dostałeś.
    Głosujesz TAK albo NIE. Jeśli nie masz przekonania lub brakuje ci danych — głosuj NIE.
    Przy TAK podaj stop-loss, take-profit i jaki % maksymalnej pozycji otworzyć.
    """


def _prompt_danych(stan: AktualnyStan, trader: KonfiguracjaTradera, cena: float, atr: float, koszt: float) -> str:
    return f"""
    Para: {stan["symbol"]} | Interwał: {stan["interwal"]}

    {zloz_dane(stan, trader.zakres_danych)}

    {opis_regul(cena, atr, koszt)}
    """


def _opinia(trader: KonfiguracjaTradera, **pola: Any) -> Dict[str, Any]:
    return {
        "nazwa": trader.nazwa,
        "model": trader.model,
        "glos": "NIE",
        "uzasadnienie": "",
        "stop_loss": None,
        "take_profit": None,
        "wielkosc_pozycji_procent": None,
        "uwagi": [],
        **pola,
    }


def zbuduj_wezel_tradera(trader: KonfiguracjaTradera) -> Callable[[AktualnyStan], Dict[str, Any]]:
    sprawdz_zakres_danych(trader.zakres_danych, f"Trader '{trader.id}'")

    def wezel(stan: AktualnyStan) -> Dict[str, Any]:
        print(f"----Trader: {trader.nazwa} ({trader.model})----")
        if not stan.get("aktualne_dane") or not stan.get("analiza_techniczna"):
            raise RuntimeError(f"Trader '{trader.id}': brak danych rynkowych lub analizy technicznej w stanie.")

        cena = cena_wejscia(stan["aktualne_dane"])
        atr = stan["analiza_techniczna"]["atr"]["wartosc"]
        koszt = koszt_transakcji_procent(stan["aktualne_dane"].get("spread_procent"))
        wiadomosci = [
            SystemMessage(content=_prompt_systemowy(trader)),
            HumanMessage(content=_prompt_danych(stan, trader, cena, atr, koszt)),
        ]

        try:
            odpowiedz = llm.zapytaj_model(trader, OpiniaTradera, wiadomosci)
        except Exception as blad:
            # Awaria jednego tradera nie zatrzymuje rundy — liczy się jako NIE
            print(f"Błąd tradera '{trader.id}': {blad}")
            return {"opinie": {trader.id: _opinia(trader, uwagi=[f"błąd wywołania modelu: {blad}"])}}

        opinia = _opinia(trader, **odpowiedz.model_dump())
        if opinia["glos"] == "TAK":
            bledy = sprawdz_sl_tp(cena, opinia["stop_loss"], opinia["take_profit"], atr, koszt)
            if bledy:
                opinia["glos"] = "NIE"
                opinia["uwagi"] = ["głos TAK unieważniony (zamieniony na NIE): " + "; ".join(bledy)]
            elif opinia["wielkosc_pozycji_procent"] is None:
                opinia["wielkosc_pozycji_procent"] = 100.0
        return {"opinie": {trader.id: opinia}}

    return wezel
