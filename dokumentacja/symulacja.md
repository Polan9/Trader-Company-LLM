# `symulacja/` — paper trading

Uruchomienie: `python -m symulacja` (pętla) / `--raz` (jeden cykl) / `python -m symulacja.raport`.

## Jak działa symulator

Co godzinę (`OPOZNIENIE_PO_ZAMKNIECIU_S` po zamknięciu świecy) jeden **cykl**:
1. **Rozliczenie** otwartych pozycji i ocen na nowych świecach (SL / TP / czas).
2. Runda dla tej świecy już w bazie → koniec (bezpieczny restart, brak podwójnych kosztów LLM).
3. Osiągnięty limit `MAKS_OTWARTYCH_POZYCJI` (domyślnie 1) → runda zapisana jako
   **pominięta**, ława nie jest zwoływana.
4. **Screener** wybiera parę (pomijając pary z otwartą pozycją). Brak pary → runda pominięta
   z symbolem `BRAK`.
5. **Przeszukiwanie rynku:** runda ławy dla pierwszej pary z rankingu; gdy ława powie NIE,
   kolejna para z rankingu (nigdy ta sama ponownie) — aż do otwarcia pozycji albo
   `MAKS_PAR_NA_SWIECE` par (domyślnie 4). Każda para to osobna runda w bazie (z rankingiem
   screenera, opiniami, zużyciem LLM, ocenami i — przy decyzji TAK — nową pozycją).

**Wejście** w pozycję liczone od świecy **po** decyzji, po cenie `ask` z chwili decyzji.
**Oceny** to transakcje hipotetyczne: referencja (SL 1×ATR, minimalny TP) w każdej rundzie
i każda opinia TAK na własnych poziomach tradera — z nich powstaje karta traderów.

## `symulacja/ocena.py` — rozstrzyganie transakcji

Zasady konserwatywne (przy niepewności gorszy wariant):
- otwarcie świecy poniżej SL (luka) → wyjście po cenie otwarcia,
- otwarcie powyżej TP → wyjście po TP,
- SL i TP w tej samej świecy → rozstrzygnięcie na świecach 1m; nadal remis → SL.

### `class WynikTransakcji`
`zamknieta`, `powod` (TP / SL / CZAS), `czas_wyjscia`, `cena_wyjscia`.

### `Rozstrzygacz`
Typ funkcji `(czas_świecy, SL, TP) → "SL" | "TP"` — kto padł pierwszy wewnątrz świecy.

### `_wyjscie_w_swiecy(swieca, stop_loss, take_profit, rozstrzygnij) -> (powod, cena) | None`
Sprawdza jedną świecę według zasad powyżej; `None` = świeca nie zamyka transakcji.

### `ocen_transakcje(swiece, czas_wejscia, stop_loss, take_profit, maks_swiec=None, rozstrzygnij=None) -> WynikTransakcji`
**Co robi:** przechodzi świece od czasu wejścia i zwraca, co padło pierwsze.
**Jak działa:** świece z `timestamp >= czas_wejscia`, najwyżej `maks_swiec`. Pierwsza świeca
z wyjściem kończy transakcję. Po `maks_swiec` bez SL/TP → **CZAS** po zamknięciu ostatniej
świecy. Za mało świec → transakcja nadal otwarta.

### `kolejnosc_w_swiecach(swiece_nizsze, stop_loss, take_profit) -> str`
Na świecach niższego interwału (1m) zwraca, czy pierwszy padł SL czy TP; brak rozstrzygnięcia → SL.

### `wynik_netto(cena_wejscia, cena_wyjscia, stop_loss, koszt_procent) -> dict`
`wynik_procent` = zmiana ceny % − koszt; `wynik_r` = wynik_procent / (odległość SL % + koszt).
Trafienie SL daje zawsze −1 R (chyba że luka pogorszyła wyjście).

## `symulacja/petla.py` — pętla

### `skonfiguruj_logi()`
Logi do konsoli i do `KATALOG_LOGOW/symulacja.log` (rotacja po 5 MB, 5 plików).

### `dlugosc_swiecy(interwal) -> Timedelta`
Długość świecy z nazwy interwału (`ccxt.parse_timeframe`).

### `ostatnia_zamknieta_swieca(teraz, interwal) -> Timestamp`
Czas otwarcia ostatniej zamkniętej świecy wg zegara: `floor(teraz) − długość`. Używana do
sprawdzenia, czy runda już była — **zanim** zapłacimy za LLM.

### `sekundy_do_nastepnej_rundy(teraz, interwal) -> float`
Sekundy do najbliższego zamknięcia świecy + `OPOZNIENIE_PO_ZAMKNIECIU_S`.

### `_rozstrzygacz(symbol, interwal) -> Rozstrzygacz`
Tworzy funkcję, która przy SL i TP w jednej świecy pobiera jej świece 1m i wywołuje `kolejnosc_w_swiecach`.

### `rozlicz_otwarte(polaczenie) -> list`
**Co robi:** zamyka pozycje i oceny, które na nowych świecach trafiły SL, TP albo limit czasu.
**Jak działa:** grupuje otwarte wpisy po (para, interwał), pobiera świece od najstarszego
wejścia jednym zapytaniem, ocenia każdy wpis `ocen_transakcje`, liczy `wynik_netto`
(dla pozycji też `wynik_usd` = wielkość × wynik %) i zapisuje w jednej transakcji bazy.
**Zwraca:** listę zamkniętych wpisów.

### `BRAK_PARY = "BRAK"`
Symbol zapisywany w rundzie pominiętej, gdy screener nie wybrał żadnej pary.

### `_skrot_screenera(wynik_screenera, liczba=10) -> dict`
Do zapisu w bazie: wybrana para, czołówka rankingu i powody odrzuceń (bez zbędnych danych).

### `_zapisz_wynik_rundy(polaczenie, wynik, zuzycie, czas_swiecy, wynik_screenera=None) -> int`
Zapisuje w **jednej transakcji**: rundę (ze szczegółami JSON, w tym rankingiem screenera),
opinie, zużycie LLM, ocenę referencyjną, oceny głosów TAK i — przy decyzji TAK — pozycję.
Zwraca id rundy.

### `wykonaj_cykl(polaczenie, graf, stan_poczatkowy, teraz=None) -> dict`
Jeden cykl (opis na górze): rozliczenie, sprawdzenie duplikatu świecy i limitu pozycji,
screener, potem `_runda_lawy` dla kolejnych par z rankingu, aż któraś otworzy pozycję.
**Zwraca:** `{"status": "runda" | "pominieta" | "brak_pary" | "juz_byla", "rundy": [...], ...}`.

### `_runda_lawy(polaczenie, graf, stan_poczatkowy, symbol, czas_swiecy, teraz, wynik_screenera) -> dict`
**Co robi:** jedna runda ławy dla jednej pary.
**Jak działa:** stan z budżetem i licznikami dziennymi z bazy → graf → zużycie LLM.
Gdy giełda zwróci inną ostatnią świecę niż wynika z zegara (opóźnienie publikacji), zapisuje
pod czasem z danych; jeśli runda dla tej pary i świecy już jest — nie zapisuje duplikatu.
**Zwraca:** `{"status", "runda_id", "symbol", "otwarta_pozycja"}`.

### `uruchom(polaczenie, graf, stan_poczatkowy, raz=False)`
Pętla główna: cykl z ponawianiem (`PROBY_CYKLU`, przerwa `PRZERWA_PO_BLEDZIE_S`), potem
sen do następnej świecy. `raz=True` — jeden cykl (testy, timer systemd).

## `symulacja/__main__.py`

### `main()`
Parsuje `--raz`, ładuje `.env`, konfiguruje logi, otwiera/inicjalizuje bazę
(`BUDZET_POCZATKOWY` tylko przy pierwszym uruchomieniu), buduje graf i uruchamia pętlę.
Ctrl+C kończy pracę i zamyka bazę.

## `symulacja/raport.py` — raport skuteczności

### `MIN_TRANSAKCJI_DO_WNIOSKOW = 100`
Poniżej tej liczby raport ostrzega, że wyniki mogą być przypadkowe (przewaga ~0.25 R przy
odchyleniu ~1.25 R potrzebuje ok. 100 transakcji do wykrycia na poziomie ~2σ).

### `_statystyki_transakcji(wyniki_r) -> dict`
Liczba, skuteczność %, średni R, suma R, profit factor (suma zysków / suma strat).

### `_maks_spadek_procent(kapital) -> float`
Największy spadek kapitału od szczytu w %.

### `_linia_statystyk(nazwa, statystyki) -> str`
Jedna linia raportu ze statystykami.

### `karta_traderow(polaczenie) -> DataFrame`
**Co robi:** trafność każdego tradera.
**Jak działa:** głos **TAK trafny**, gdy jego własna transakcja hipotetyczna zarobiła;
głos **NIE trafny**, gdy transakcja referencyjna z tej rundy straciła. Liczone tylko
rozstrzygnięte. Kolumny: głosy, % TAK, rozstrzygnięte, trafność (ogółem / TAK / NIE), średni R z TAK.

### `zbuduj_raport(polaczenie) -> str`
Pełny raport: okres i rundy, portfel (budżet, koszt LLM, wynik po LLM), transakcje ławy
(skuteczność, R, profit factor, maks. spadek, czas, powody wyjść), strategie odniesienia
(**zawsze wchodź**, **heurystyka RSI/MACD**, **kup i trzymaj**), karta traderów, ostrzeżenie o małej próbie.
