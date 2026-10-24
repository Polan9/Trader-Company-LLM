"""Head Trader — wybiera SL/TP z zakresu propozycji ławy; fallback na medianę."""
from typing import Any, Callable, Dict

from langchain_core.messages import HumanMessage, SystemMessage

from dane.gielda import cena_wejscia
from konfiguracja.lawa import KonfiguracjaHeadTradera
from lawa import llm
from lawa.modele import DecyzjaHeadTradera
from lawa.sl_tp import koszt_transakcji_procent, opis_regul, sprawdz_sl_tp, w_zakresie
from stan import AktualnyStan


def _formatuj_opinie(stan: AktualnyStan) -> str:
    linie = []
    for opinia in stan["opinie"].values():
        poziomy = (
            f" | SL {opinia['stop_loss']:.8g} | TP {opinia['take_profit']:.8g} | skala pozycji {opinia['wielkosc_pozycji_procent']:.0f}%"
            if opinia["glos"] == "TAK" else ""
        )
        linie.append(f"- {opinia['nazwa']}: {opinia['glos']}{poziomy}\n  Uzasadnienie: {opinia['uzasadnienie']}")
    return "\n".join(linie)


def _prompt(stan: AktualnyStan, cena: float, atr: float, koszt: float) -> str:
    wynik = stan["wynik_glosowania"]
    sl, tp = wynik["stop_loss"], wynik["take_profit"]
    return f"""
    Para: {stan["symbol"]} | Interwał: {stan["interwal"]}
    Wynik głosowania: {wynik['tak']} TAK / {wynik['nie']} NIE — pozycja zostanie otwarta.

    OPINIE ŁAWY:
    {_formatuj_opinie(stan)}

    ZAKRES PROPOZYCJI (od traderów głosujących TAK):
    - Stop-loss: min {sl['min']:.8g} | mediana {sl['mediana']:.8g} | max {sl['max']:.8g}
    - Take-profit: min {tp['min']:.8g} | mediana {tp['mediana']:.8g} | max {tp['max']:.8g}

    {opis_regul(cena, atr, koszt)}

    Wybierz stop-loss i take-profit WEWNĄTRZ powyższych zakresów (wartości spoza zakresu
    zostaną odrzucone i zastąpione medianą). Uwzględnij argumenty traderów głosujących NIE
    jako ryzyka.
    """


def zbuduj_wezel_head_tradera(konfiguracja: KonfiguracjaHeadTradera) -> Callable[[AktualnyStan], Dict[str, Any]]:
    def wezel(stan: AktualnyStan) -> Dict[str, Any]:
        print(f"----Head Trader ({konfiguracja.model})----")
        wynik = stan["wynik_glosowania"]
        cena = cena_wejscia(stan["aktualne_dane"])
        atr = stan["analiza_techniczna"]["atr"]["wartosc"]
        koszt = koszt_transakcji_procent(stan["aktualne_dane"].get("spread_procent"))
        mediana = {
            "stop_loss": wynik["stop_loss"]["mediana"],
            "take_profit": wynik["take_profit"]["mediana"],
            "uzasadnienie": "mediana propozycji ławy",
            "zrodlo": "mediana",
            "uwagi": [],
        }

        wiadomosci = [
            SystemMessage(content=konfiguracja.osobowosc),
            HumanMessage(content=_prompt(stan, cena, atr, koszt)),
        ]
        try:
            odpowiedz = llm.zapytaj_model(konfiguracja, DecyzjaHeadTradera, wiadomosci, kto="head_trader")
        except Exception as blad:
            print(f"Błąd Head Tradera: {blad}")
            return {"decyzja_head_tradera": {**mediana, "uwagi": [f"błąd wywołania modelu: {blad}"]}}

        uwagi = []
        if not w_zakresie(odpowiedz.stop_loss, wynik["stop_loss"]):
            uwagi.append(f"SL {odpowiedz.stop_loss:.8g} poza zakresem propozycji")
        if not w_zakresie(odpowiedz.take_profit, wynik["take_profit"]):
            uwagi.append(f"TP {odpowiedz.take_profit:.8g} poza zakresem propozycji")
        uwagi += sprawdz_sl_tp(cena, odpowiedz.stop_loss, odpowiedz.take_profit, atr, koszt)
        if uwagi:
            return {"decyzja_head_tradera": {**mediana, "uwagi": ["decyzja Head Tradera odrzucona: " + "; ".join(uwagi)]}}

        return {"decyzja_head_tradera": {**odpowiedz.model_dump(), "zrodlo": "head_trader", "uwagi": []}}

    return wezel
