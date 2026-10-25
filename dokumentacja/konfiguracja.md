# `konfiguracja/`

## `konfiguracja/ustawienia.py` — stałe

Same stałe, bez funkcji. Najważniejsze grupy:

| Grupa | Stałe | Znaczenie |
|---|---|---|
| Ścieżki | `KATALOG_PROJEKTU`, `PLIK_ENV`, `PLIK_STANU`, `PLIK_KONFIGURACJI_LAWY` | pliki projektu |
| | `KATALOG_DANYCH` | katalog bazy i logów; nadpisywany zmienną środowiskową `TRADER_KATALOG_DANYCH` (na Raspberry Pi — katalog na SSD) |
| | `PLIK_BAZY`, `KATALOG_LOGOW` | `trader.db` i `logi/` w `KATALOG_DANYCH` |
| Tryb | `TRYB` | `symulacja` / `testnet` / `realny` — na razie zlecenia nie są składane |
| Rynek | `SYMBOL`, `INTERWAL`, `BUDZET_POCZATKOWY` | BTC/USDT, 1h, 1000 USD |
| Koszty | `PROWIZJA_STRONA_PROCENT`, `POSLIZG_STRONA_PROCENT` | założenia — do kalibracji po żywym teście |
| Ryzyko | `RYZYKO_NA_TRANSAKCJE_PROCENT`, `MAKS_POZYCJA_PROCENT_BUDZETU`, `MIN_WIELKOSC_POZYCJI_USD`, `MAKS_DZIENNA_STRATA_PROCENT`, `MAKS_TRANSAKCJI_DZIENNIE` | twarde limity Risk Managera |
| | `MIN_ZYSK_DO_RYZYKA`, `TOLERANCJA_ZYSK_DO_RYZYKA`, `MIN_SL_ATR`, `MAKS_SL_ATR` | reguły SL/TP |
| Screener | `SCREENER_WLACZONY` | `False` = ława zawsze analizuje `SYMBOL` |
| | `SCREENER_LICZBA_KANDYDATOW`, `SCREENER_MIN_WOLUMEN_USDT`, `SCREENER_MAKS_SPREAD_PROCENT`, `SCREENER_MAKS_KOSZT_DO_ATR`, `SCREENER_MIN_ATR_PROCENT`, `SCREENER_OKNO_ATR`, `SCREENER_SWIECE` | kryteria wyboru pary — opis w [screener.md](screener.md) |
| | `WYKLUCZONE_AKTYWA` | ręczna lista stablecoinów i tokenizowanych akcji/złota |
| | `MAKS_OTWARTYCH_POZYCJI` | limit otwartych pozycji łącznie na wszystkich parach (1) |
| | `MAKS_PAR_NA_SWIECE` | ile par z rankingu ława może przeanalizować w jednej świecy, gdy poprzednie dostały NIE (6) |
| Symulator | `OPOZNIENIE_PO_ZAMKNIECIU_S` | ile sekund po zamknięciu świecy startuje runda |
| | `PROBY_CYKLU`, `PRZERWA_PO_BLEDZIE_S` | ponawianie cyklu po błędzie |
| | `MAKS_CZAS_POZYCJI_SWIEC` | zamknięcie pozycji po czasie (24 świece = doba przy 1h) |
| | `INTERWAL_ROZSTRZYGANIA` | `1m` — gdy SL i TP w jednej świecy |
| | `REFERENCJA_SL_ATR` | SL transakcji referencyjnej (1×ATR) |
| Świece | `LIMIT_SWIEC`, `MIN_SWIEC`, `SWIECE_W_PROMPCIE`, `SWIECE_KROTKIE_W_PROMPCIE` | ile świec pobrać / pokazać |
| Wskaźniki | `OKRES_RSI`, `MACD_*`, `OKRES_ATR`, `OKRES_SREDNIEGO_WOLUMENU`, `OKRES_TRENDU_WOLUMENU`, `PROG_TRENDU_WOLUMENU` | parametry wskaźników |
| Cennik | `CENNIK_MODELI` | `model → (wejście, wejście z cache, wyjście)` USD/1M tokenów — aktualizować ręcznie |
| Statystyki | `OKNO_KROTKIE`, `OKNO_DLUGIE`, `OKNO_ZSCORE`, `OKNO_ZAKRESU`, `OKNO_AUTOKORELACJI` | okna statystyk quanta |

## `konfiguracja/lawa.json` — role ławy

Dane, nie kod (docelowo edytowane z UI). Lista `traderzy` i obiekt `head_trader`.
Pola tradera: `id` (nazwa węzła), `nazwa`, `aktywny`, `osobowosc`, `fokus`, `model`,
`temperatura` (null dla modeli rozumujących), `reasoning_effort`, `zakres_danych`
(nazwy bloków z `lawa/bloki_danych.py`).

## `konfiguracja/lawa.py` — wczytanie i walidacja

### `class KonfiguracjaModelu(BaseModel)`
Wspólne pola modelu LLM: `model`, `temperatura`, `reasoning_effort`. Używana przez `lawa/llm.py`.

### `class KonfiguracjaTradera(KonfiguracjaModelu)`
Pola tradera z `lawa.json`. `id` musi pasować do wzorca `^[a-z][a-z0-9_]*$`, bo jest nazwą węzła grafu.

### `class KonfiguracjaHeadTradera(KonfiguracjaModelu)`
`nazwa` i `osobowosc` (prompt systemowy) Head Tradera.

### `class KonfiguracjaLawy(BaseModel)`
Całość pliku. **`aktywni_traderzy`** (właściwość) — lista traderów z `aktywny: true`.

### `wczytaj_konfiguracje_lawy(sciezka=PLIK_KONFIGURACJI_LAWY) -> KonfiguracjaLawy`
**Co robi:** wczytuje `lawa.json` i sprawdza poprawność.
**Jak działa:** pydantic waliduje typy i pola; dodatkowo błąd, gdy `id` traderów się
powtarzają albo nie ma żadnego aktywnego tradera. Nazwy bloków danych sprawdza dopiero
`zbuduj_wezel_tradera` (przy budowie grafu).
