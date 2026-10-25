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

### `statystyki_transakcji(wyniki_r) -> dict`
Liczba, skuteczność %, średni R, suma R, profit factor (suma zysków / suma strat).

### `maks_spadek_procent(kapital) -> float`
Największy spadek kapitału od szczytu w %.

### `PARA_BENCHMARKU = "BTC/USDT"`
Para używana jako benchmark całego rynku.

### `kup_i_trzymaj_btc(rundy) -> dict | None`
**Co robi:** wynik kupienia BTC na starcie symulacji i trzymania do teraz.
**Jak działa:** świece BTC od świecy pierwszej rundy; zamknięcie pierwszej → zamknięcie ostatniej
zamkniętej świecy. Zwraca `start`, `koniec`, `zmiana_procent` i `netto_procent` (minus koszt
wejścia i wyjścia przy zerowym spreadzie). Pobiera dane z giełdy.

### `kup_i_trzymaj_pary(rundy) -> DataFrame`
**Co robi:** dla każdej pary, którą analizowała ława — kupno po cenie z **pierwszej rundy na tej
parze** i wycena po aktualnej cenie.
**Jak działa:** pierwsza niepominięta runda per para, aktualne ceny jednym zapytaniem
(`aktualne_ceny`), wynik netto = zmiana ceny − koszt transakcji z tej rundy.
Kolumny: `symbol`, `czas_swiecy`, `cena_wejscia`, `cena_teraz`, `zmiana_procent`, `netto_procent`.
Liczone osobno per para, bo screener wybiera różne coiny — porównanie cen różnych par nie ma sensu.

### `otwarte_oceny_na_zywo(polaczenie) -> DataFrame`
**Co robi:** nierozstrzygnięte transakcje hipotetyczne (referencje i głosy TAK) wycenione po
**aktualnej** cenie — niezrealizowany wynik.
**Jak działa:** otwarte oceny + nazwa tradera z opinii, aktualne ceny jednym zapytaniem;
liczy wynik netto % i w R, odległość ceny do SL i do TP w %, ile godzin trwa.
Uwaga: rozstrzyganie w symulatorze odbywa się na **zamkniętych** świecach co godzinę —
cena chwilowo poniżej SL (ujemne „do SL”) zamknie ocenę dopiero w najbliższym cyklu.

### `formatuj_otwarte_oceny(oceny) -> str`
Tabela otwartych ocen do raportu (para, kto, wejście, cena teraz, wynik %, R, do SL, do TP,
godziny) i podsumowanie: liczba referencji / głosów TAK, średni niezrealizowany R.

### `_linia_statystyk(nazwa, statystyki) -> str`
Jedna linia raportu ze statystykami.

### `opinie_z_ocenami(polaczenie) -> DataFrame`
Każda opinia (z pewnością) połączona z wynikiem: głos TAK → własna transakcja hipotetyczna tradera,
głos NIE → referencja z tej rundy. Kolumny dodatkowe: `rozstrzygnieta`, `trafna`, `wynik_r`.
Wspólna podstawa karty traderów i trafności wg pewności.

### `karta_traderow(polaczenie) -> DataFrame`
**Co robi:** trafność każdego tradera.
**Jak działa:** głos **TAK trafny**, gdy jego własna transakcja hipotetyczna zarobiła;
głos **NIE trafny**, gdy transakcja referencyjna z tej rundy straciła. Liczone tylko
rozstrzygnięte. **Osobny wiersz dla każdej pary trader + model** — po zmianie modelu tradera widać
wyniki przed i po (np. scalper na gpt-5-nano i na gpt-5.6-luna). Kolumny: trader, model, głosy, % TAK,
rozstrzygnięte, trafność (ogółem / TAK / NIE), średni R z TAK, średnia deklarowana pewność.

### `PRZEDZIALY_PEWNOSCI` i `trafnosc_wg_pewnosci(polaczenie) -> DataFrame`
**Co robi:** sprawdza, czy deklarowana pewność coś znaczy — trafność rozstrzygniętych głosów TAK
i NIE osobno w przedziałach pewności 0–49, 50–69, 70–84, 85–100.
**Kolumny:** `glos`, `przedzial`, `liczba`, `trafnosc_procent`, `sredni_r` (dla NIE: średni wynik
referencji — ujemny = NIE uchroniło przed stratą). Głosy bez pewności (sprzed 2026-10-25,
unieważnione TAK) są pomijane. Podstawa decyzji o ewentualnym „force” (patrz CLAUDE.md).

### `zbuduj_raport(polaczenie) -> str`
Pełny raport: okres i rundy, portfel (budżet, koszt LLM, wynik po LLM), transakcje ławy
(skuteczność, R, profit factor, maks. spadek, czas, powody wyjść), strategie odniesienia
(**zawsze wchodź**, **heurystyka RSI/MACD**, **kup i trzymaj BTC** jako benchmark rynku
i **kup i trzymaj pary** — średnia i lista per para), **otwarte oceny wycenione na żywo**,
karta traderów, **trafność wg pewności**, ostrzeżenie o małej próbie.
Gdy giełda jest niedostępna, sekcja „kup i trzymaj” pokazuje komunikat, reszta raportu działa.
