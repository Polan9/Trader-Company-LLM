# `zapis/` — baza danych i plik stanu

## `zapis/baza.py` — SQLite (tryb WAL)

Jedyne miejsce w kodzie, które zna silnik bazy — zmiana na PostgreSQL = wymiana tego pliku.
Czasy jako tekst ISO 8601 w UTC. **Budżet nie jest zapisywany wprost**: aktualny budżet =
budżet początkowy + suma wyników zamkniętych pozycji (jedno źródło prawdy).

### Tabele

| Tabela | Zawartość |
|---|---|
| `portfel` | jeden wiersz: budżet początkowy i data utworzenia |
| `rundy` | każda runda (także pominięta), unikalna per (para, interwał, świeca) — w jednej świecy może być kilka par z przeszukiwania; para z rankingu screenera (`BRAK`, gdy żadna nie przeszła); cena, ATR, koszt, decyzja, koszt LLM, szczegóły JSON (z rankingiem screenera) |
| `opinie` | głos każdego tradera w rundzie: uzasadnienie, SL/TP, skala, uwagi |
| `oceny` | transakcje hipotetyczne (referencja + głosy TAK) i ich wynik — do karty traderów |
| `pozycje` | wirtualne pozycje ławy: wejście, SL/TP, wielkość, ryzyko, wynik USD/%/R |
| `zuzycie_llm` | tokeny i koszt każdego wywołania modelu |

### `_czas(wartosc) -> str | None`
Timestamp → tekst ISO w UTC.

### `_json(wartosc) -> str`
Serializacja do JSON z polskimi znakami; nieznane typy (np. Timestamp) jako tekst.

### `polacz(sciezka) -> Connection`
Tworzy katalog, otwiera bazę, włącza **WAL** (odporność na utratę zasilania, równoległy
odczyt) i klucze obce. Wiersze dostępne po nazwach kolumn.

### `inicjalizuj(polaczenie, budzet_poczatkowy)`
Tworzy tabele (jeśli nie ma) i portfel. **Budżet ustawiany tylko raz** — kolejne
uruchomienia go nie zmieniają (`INSERT OR IGNORE`).

### `budzet_poczatkowy(polaczenie) -> float`
Budżet z tabeli `portfel`.

### `aktualny_budzet(polaczenie) -> float`
Budżet początkowy + suma `wynik_usd` zamkniętych pozycji.

### `liczniki_dzienne(polaczenie, dzien) -> dict`
Dla doby UTC: `dzienna_strata_procent` (strata z pozycji zamkniętych dziś, w % aktualnego
budżetu; zysk = 0) i `transakcje_dzisiaj` (pozycje otwarte dziś). Dane dla Risk Managera.

### `runda_istnieje(polaczenie, symbol, interwal, czas_swiecy) -> bool`
Czy runda dla tej pary i świecy jest już zapisana — ochrona przed duplikatem przy przeszukiwaniu kilku par.

### `runda_dla_swiecy_istnieje(polaczenie, interwal, czas_swiecy) -> bool`
Czy dla tej świecy była już jakakolwiek runda (dowolna para). Na początku cyklu: po restarcie
w tej samej godzinie przeszukiwanie nie jest powtarzane (brak podwójnych kosztów LLM).

### `zapisz_runde(polaczenie, **pola) -> int`
Wstawia rundę; uzupełnia wartości domyślne, konwertuje czas i pola JSON. Zwraca id.

### `zapisz_opinie(polaczenie, runda_id, opinie)`
Wstawia opinie wszystkich traderów rundy.

### `zapisz_zuzycie(polaczenie, runda_id, zuzycie)`
Wstawia wpisy zużycia LLM z `pobierz_i_wyczysc_zuzycie`.

### `zapisz_ocene(polaczenie, runda_id, kto, symbol, interwal, czas_wejscia, cena_wejscia, stop_loss, take_profit, koszt_procent) -> int`
Wstawia transakcję hipotetyczną ze statusem `otwarta`.

### `zapisz_pozycje(polaczenie, runda_id, symbol, interwal, czas_wejscia, decyzja) -> int`
Wstawia wirtualną pozycję z `decyzja_koncowa` Risk Managera.

### `otwarte(polaczenie, tabela) -> list[Row]`
Otwarte wpisy z `pozycje` albo `oceny` (inne nazwy tabel → błąd, ochrona przed wstrzyknięciem SQL).
Dla pozycji — podstawa limitu `MAKS_OTWARTYCH_POZYCJI` i listy par pomijanych przez screener.

### `zamknij(polaczenie, tabela, id_, **wynik)`
Ustawia status `zamknieta` i pola wyniku (powód, czas i cena wyjścia, wynik %, R, ew. USD).

### `tabela_jako_df(polaczenie, zapytanie, parametry=()) -> DataFrame`
Wynik zapytania SQL jako DataFrame — dla raportu.

> Uwaga: funkcje zapisu nie robią `commit` same — wywołujący grupuje je w `with polaczenie:`,
> żeby runda zapisała się w całości albo wcale.

## `zapis/odczyt.py` — odczyty dla interfejsu
Zapytania tylko do odczytu (połączenie `mode=ro`) używane przez API — opis w [api.md](api.md).

## `zapis/plik_stanu.py` — czytelny podgląd ostatniej rundy

### `_slownik(dane) -> list[str]`
Linie `klucz: wartość` (albo „(brak)”).

### `_opinie(opinie) -> list[str]`
Opinie traderów: głos, SL/TP i skala (przy TAK), uzasadnienie, uwagi.

### `formatuj_zuzycie(zuzycie) -> str`
Tabela tokenów i kosztu każdego wywołania LLM oraz suma.

### `zapisz_stan(stan, zuzycie=None, nazwa_pliku=PLIK_STANU)`
Zapisuje pełny stan rundy do `trading_state.txt`: koszt LLM, decyzję końcową, głosowanie,
opinie, Head Tradera, ticker, analizę techniczną, statystyki i ostatnie świece.
Nadpisywany co rundę — historia jest w bazie.
