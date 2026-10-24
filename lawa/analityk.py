"""Pojedynczy analityk ze szkicu — do zastąpienia ławą traderów."""
from functools import lru_cache

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from dane.gielda import formatuj_swiece, formatuj_ticker
from konfiguracja.ustawienia import MODEL_ANALITYKA
from stan import AktualnyStan
from wskazniki.analiza_techniczna import formatuj_analize_techniczna


@lru_cache(maxsize=1)
def _llm_analityka() -> ChatOpenAI:
    # Tworzony przy pierwszym użyciu — import modułu nie wymaga klucza API.
    return ChatOpenAI(model=MODEL_ANALITYKA, temperature=0)


def analityk(stan: AktualnyStan):
    print("----Analityk----")
    aktualne_dane = stan["aktualne_dane"]

    if not aktualne_dane or aktualne_dane.get("last") is None:
        raise RuntimeError(
            "Brak danych rynkowych w stanie — węzeł 'pobierz_dane' nie uzupełnił aktualne_dane."
        )

    prompt = f"""
    Jesteś profesjonalnym analitykiem rynku kryptowalut, twoim zadaniem jest:
    - analiza danej pary i dostępnych danych,
    - propozycja ruchu na giełdzie,
    - podjęcie wstępnej decyzji,
    - przygotowanie raportu z propozycjami dla head tradera.

    Para: {stan["symbol"]}
    Interwał: {stan["interwal"]}
    Aktualne dostępne saldo w USD: {stan["budzet"]}

    {formatuj_ticker(aktualne_dane)}

    {formatuj_analize_techniczna(stan.get("analiza_techniczna", {}))}

    {formatuj_swiece(stan["dane_historyczne"], stan["interwal"])}

    Uwzględnij szczególnie analizę techniczną (wolumen, RSI, MACD, ATR) przy ocenie momentów wejścia i wyjścia.

    Przeanalizuj te dane i podaj decyzję inwestycyjną w formacie:
    1. DECYZJA: [KUPUJ / SPRZEDAJ / CZEKAJ]
    2. UZASADNIENIE: wyjaśnienie dla kolejnych osób w zespole.
    3. POZIOM STOP-LOSS: sugerowana cena zabezpieczenia.
    4. POZIOM TAKE-PROFIT: sugerowane wyjście z pozycji oraz potencjalny zarobek.
    5. WIELKOŚĆ POZYCJI: za ile USD z budżetu otworzyć pozycję.

    JEŚLI PODCZAS ANALIZY BRAKUJE CI DANYCH, NARZĘDZI LUB CZEGOKOLWIEK, CO POMOGŁOBY W ANALIZIE, DOPISZ TO NA SAMYM KOŃCU.
    """

    odpowiedz = _llm_analityka().invoke([HumanMessage(content=prompt)])
    print("Analiza zakończona.")
    return {"decyzja_analityka": odpowiedz.content}
