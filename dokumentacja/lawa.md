# `lawa/` — traderzy, głosowanie, Head Trader, Risk Manager

## `lawa/bloki_danych.py` — z czego składany jest prompt tradera

### `BLOKI_DANYCH: Dict[str, Callable[[stan], str]]`
Rejestr: nazwa bloku z `zakres_danych` → funkcja zwracająca tekst. Bloki: `ticker`,
`swiece`, `swiece_krotkie`, `wolumen`, `rsi`, `macd`, `atr`, `sygnaly_heurystyczne`,
`statystyki`, `newsy`. Nowy blok = nowa pozycja w słowniku; konfiguracja ról się nie zmienia.

### `_blok_newsy(stan) -> str`
Tymczasowy blok `newsy` — informuje, że moduł newsów jest niedostępny.

### `sprawdz_zakres_danych(zakres_danych, kto)`
Rzuca `ValueError` z listą dostępnych bloków, gdy konfiguracja zawiera nieznaną nazwę.

### `zloz_dane(stan, zakres_danych) -> str`
Skleja teksty bloków w kolejności z konfiguracji tradera.

## `lawa/modele.py` — schematy odpowiedzi LLM (pydantic)

### `class OpiniaTradera`
`glos` (TAK/NIE), `uzasadnienie`, `stop_loss`, `take_profit`, `wielkosc_pozycji_procent`
(**skala 0–100 pełnej pozycji**, nie % budżetu). Opisy pól trafiają do schematu,
który widzi model — to część instrukcji.

### `class DecyzjaHeadTradera`
`stop_loss`, `take_profit`, `uzasadnienie`.

## `lawa/llm.py` — jedyne miejsce wywołań LLM

### `_klient(model, temperatura, reasoning_effort) -> ChatOpenAI`
Tworzy klienta raz na zestaw parametrów (`lru_cache`). `temperature` / `reasoning_effort`
przekazywane tylko, gdy ustawione (modele rozumujące nie wspierają `temperature`).

### `_koszt_usd(model, wejscie, z_cache, wyjscie) -> float | None`
Koszt wywołania z `CENNIK_MODELI` (tokeny z cache po tańszej stawce). `None`, gdy modelu brak w cenniku.

### `_zapisz_zuzycie(kto, model, odpowiedz)`
Czyta `usage_metadata` (tokeny wejścia, wyjścia, rozumowania, cache) i dopisuje wpis
do rejestru — pod blokadą, bo traderzy działają równolegle.

### `zapytaj_model(konfiguracja, schemat, wiadomosci, kto="") -> schemat`
**Co robi:** wywołuje model i zwraca odpowiedź jako obiekt pydantic.
**Jak działa:** `with_structured_output(schemat, include_raw=True)` — dostajemy i obiekt,
i surową odpowiedź (z zużyciem tokenów); zapisuje zużycie; błąd parsowania rzucany dalej.
W testach podmieniany atrapą (`lawa.llm.zapytaj_model = ...`).

### `pobierz_i_wyczysc_zuzycie() -> list`
Zwraca zebrane wpisy zużycia i czyści rejestr (wołane po każdej rundzie).

## `lawa/sl_tp.py` — twarde reguły (kod, nie LLM)

Wszystkie rachunki **po kosztach**: zysk netto = TP − cena − koszt, ryzyko netto = cena − SL + koszt.

### `koszt_transakcji_procent(spread_procent) -> float`
`2 × (prowizja + poślizg) + spread` w % wartości pozycji.

### `zysk_do_ryzyka_netto(cena, stop_loss, take_profit, koszt_procent) -> float`
Stosunek zysku netto do ryzyka netto (koszt przeliczony na cenę: `cena × koszt% / 100`).

### `minimalny_take_profit(cena, stop_loss, koszt_procent) -> float`
Najbliższy TP spełniający `MIN_ZYSK_DO_RYZYKA` po kosztach:
`cena + koszt + 1.5 × (cena − SL + koszt)`.

### `opis_regul(cena, atr, koszt_procent) -> str`
Tekst reguł do promptów — zakres SL w cenach, wzór zysk/ryzyko i przykładowy minimalny TP
dla SL = 1×ATR. Te same reguły sprawdza potem `sprawdz_sl_tp`.

### `sprawdz_sl_tp(cena, stop_loss, take_profit, atr, koszt_procent) -> list[str]`
**Co robi:** zwraca listę naruszeń (pusta = poprawne).
**Sprawdza:** SL i TP podane; SL poniżej ceny, TP powyżej; zysk/ryzyko netto ≥ 1.5
(z tolerancją `TOLERANCJA_ZYSK_DO_RYZYKA` na zaokrąglenia); odległość SL w 0.5–3 × ATR.

### `statystyki_poziomow(wartosci) -> dict`
Mediana, minimum, maksimum listy cen (SL albo TP z głosów TAK).

### `w_zakresie(wartosc, zakres, tolerancja=1e-9) -> bool`
Czy wartość mieści się w `[min, max]` (z drobną tolerancją na arytmetykę zmiennoprzecinkową).

### `oblicz_wielkosc_pozycji(budzet, cena, stop_loss, koszt_procent, skala_procent) -> dict`
**Co robi:** wielkość pozycji tak, by trafienie SL (z kosztami) kosztowało `RYZYKO_NA_TRANSAKCJE_PROCENT` budżetu.
**Jak działa:** `ryzyko_usd / strata_%_przy_SL`, potem limit `MAKS_POZYCJA_PROCENT_BUDZETU`,
potem skala od ławy (0–100%). **Zwraca:** `wielkosc_usd`, `ryzyko_usd`, `strata_procent_przy_sl`,
`koszt_procent`, `ograniczona_limitem`.

## `lawa/traderzy.py` — fabryka traderów

### `_prompt_systemowy(trader) -> str`
Osobowość, rola, specjalizacja i zasady ławy (niezależny głos, niepewność = NIE, znaczenie skali pozycji).

### `_prompt_danych(stan, trader, cena, atr, koszt) -> str`
Para, interwał, bloki z `zakres_danych` tradera i `opis_regul`.

### `_opinia(trader, **pola) -> dict`
Słownik opinii z wartościami domyślnymi (głos NIE, puste poziomy, lista uwag).

### `zbuduj_wezel_tradera(trader) -> funkcja węzła`
**Co robi:** tworzy węzeł grafu dla jednej konfiguracji tradera.
**Jak działa (węzeł):**
1. sprawdza, że w stanie są dane i analiza,
2. wywołuje model przez `llm.zapytaj_model` (schemat `OpiniaTradera`),
3. błąd modelu → opinia NIE z uwagą (runda trwa dalej),
4. głos TAK łamiący `sprawdz_sl_tp` → zamieniany na NIE z uwagą,
5. ważny TAK bez skali → skala 100.

**Zwraca (węzeł):** `{"opinie": {id_tradera: opinia}}` — scalane reducerem w stanie.
Nazwy bloków danych sprawdzane już przy tworzeniu węzła.

## `lawa/glosowanie.py`

### `glosowanie(stan) -> dict` *(węzeł grafu)*
**Co robi:** liczy głosy i przygotowuje dane dla Head Tradera.
**Jak działa:** decyzja TAK, gdy `TAK > NIE` (remis = NIE). Przy TAK: mediana/min/max SL i TP
oraz mediana skali pozycji z głosów TAK. Przy NIE ustawia od razu `decyzja_koncowa`
(nie otwieraj, powód „ława przeciw”).

### `po_glosowaniu(stan) -> str`
Krawędź warunkowa: `"head_trader"` przy TAK, `"koniec"` przy NIE.

## `lawa/head_trader.py`

### `_formatuj_opinie(stan) -> str`
Lista opinii wszystkich traderów (także NIE, z uzasadnieniem) dla promptu Head Tradera.

### `_prompt(stan, cena, atr, koszt) -> str`
Wynik głosowania, opinie, zakres propozycji SL/TP, reguły i polecenie wyboru wewnątrz zakresu.

### `zbuduj_wezel_head_tradera(konfiguracja) -> funkcja węzła`
**Jak działa (węzeł):** wywołuje model (`DecyzjaHeadTradera`). Odrzuca decyzję i bierze
**medianę**, gdy: błąd modelu, SL/TP poza zakresem propozycji albo naruszenie `sprawdz_sl_tp`.
**Zwraca:** `{"decyzja_head_tradera": {stop_loss, take_profit, uzasadnienie, zrodlo, uwagi}}`.

## `lawa/risk_manager.py`

### `risk_manager(stan) -> dict` *(węzeł grafu)*
**Co robi:** ostatnie słowo — weto albo zatwierdzenie z wielkością pozycji.
**Weto, gdy:** SL/TP łamią reguły, osiągnięta dzienna strata (`MAKS_DZIENNA_STRATA_PROCENT`)
lub limit transakcji (`MAKS_TRANSAKCJI_DZIENNIE`), pozycja < `MIN_WIELKOSC_POZYCJI_USD`.
**Zwraca:** `decyzja_koncowa` z `otworz_pozycje`, powodami, trybem, ceną wejścia, SL/TP,
wynikiem `oblicz_wielkosc_pozycji` i `zysk_do_ryzyka_netto`.
