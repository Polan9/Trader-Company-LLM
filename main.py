import pandas as pd
from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph

from dane.gielda import pobierz_dane
from konfiguracja.ustawienia import BUDZET_POCZATKOWY, INTERWAL, PLIK_ENV, SYMBOL
from lawa.analityk import analityk
from stan import AktualnyStan
from wskazniki.analiza_techniczna import oblicz_analize_techniczna
from zapis.plik_stanu import zapisz_stan


def zbuduj_graf():
    graf = StateGraph(AktualnyStan)

    graf.add_node("pobierz_dane", pobierz_dane)
    graf.add_node("analiza_techniczna", oblicz_analize_techniczna)
    graf.add_node("analityk", analityk)

    graf.add_edge(START, "pobierz_dane")
    graf.add_edge("pobierz_dane", "analiza_techniczna")
    graf.add_edge("analiza_techniczna", "analityk")
    graf.add_edge("analityk", END)

    return graf.compile()


if __name__ == "__main__":
    load_dotenv(PLIK_ENV)

    stan_poczatkowy: AktualnyStan = {
        "symbol": SYMBOL,
        "interwal": INTERWAL,
        "aktualne_dane": {},
        "dane_historyczne": pd.DataFrame(),
        "analiza_techniczna": {},
        "decyzja_analityka": "",
        "decyzja_head_tradera": "",
        "budzet": BUDZET_POCZATKOWY,
    }

    aplikacja = zbuduj_graf()
    wynik = aplikacja.invoke(stan_poczatkowy)
    zapisz_stan(wynik)
