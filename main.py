import pandas as pd
from dotenv import load_dotenv
from langgraph.graph import END, START, StateGraph

from dane.gielda import pobierz_dane
from konfiguracja.lawa import KonfiguracjaLawy, wczytaj_konfiguracje_lawy
from konfiguracja.ustawienia import BUDZET_POCZATKOWY, INTERWAL, PLIK_ENV, SYMBOL
from lawa.glosowanie import glosowanie, po_glosowaniu
from lawa.head_trader import zbuduj_wezel_head_tradera
from lawa.risk_manager import risk_manager
from lawa.traderzy import zbuduj_wezel_tradera
from stan import AktualnyStan
from wskazniki.analiza_techniczna import oblicz_analize_techniczna
from zapis.plik_stanu import zapisz_stan


def zbuduj_graf(konfiguracja: KonfiguracjaLawy):
    graf = StateGraph(AktualnyStan)

    graf.add_node("pobierz_dane", pobierz_dane)
    graf.add_node("analiza_techniczna", oblicz_analize_techniczna)
    graf.add_node("glosowanie", glosowanie)
    graf.add_node("head_trader", zbuduj_wezel_head_tradera(konfiguracja.head_trader))
    graf.add_node("risk_manager", risk_manager)

    graf.add_edge(START, "pobierz_dane")
    graf.add_edge("pobierz_dane", "analiza_techniczna")

    # Fan-out: wszyscy aktywni traderzy równolegle, głosowanie czeka na komplet opinii
    wezly_traderow = []
    for trader in konfiguracja.aktywni_traderzy:
        wezel = f"trader_{trader.id}"
        graf.add_node(wezel, zbuduj_wezel_tradera(trader))
        graf.add_edge("analiza_techniczna", wezel)
        wezly_traderow.append(wezel)
    graf.add_edge(wezly_traderow, "glosowanie")

    graf.add_conditional_edges("glosowanie", po_glosowaniu, {"head_trader": "head_trader", "koniec": END})
    graf.add_edge("head_trader", "risk_manager")
    graf.add_edge("risk_manager", END)

    return graf.compile()


def stan_poczatkowy() -> AktualnyStan:
    return {
        "symbol": SYMBOL,
        "interwal": INTERWAL,
        "budzet": BUDZET_POCZATKOWY,
        "aktualne_dane": {},
        "dane_historyczne": pd.DataFrame(),
        "analiza_techniczna": {},
        "opinie": {},
        "wynik_glosowania": {},
        "decyzja_head_tradera": {},
        "decyzja_koncowa": {},
        "dzienna_strata_procent": 0.0,
        "transakcje_dzisiaj": 0,
    }


if __name__ == "__main__":
    load_dotenv(PLIK_ENV)

    aplikacja = zbuduj_graf(wczytaj_konfiguracje_lawy())
    wynik = aplikacja.invoke(stan_poczatkowy())
    zapisz_stan(wynik)
