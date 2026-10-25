# `dane/gielda.py` — dane z Binance

### `tylko_zamkniete_swiece(surowe_swiece, interwal, teraz_ms) -> list`
**Co robi:** odrzuca świecę, która jeszcze trwa.
**Jak działa:** świeca jest zamknięta, gdy `czas_otwarcia + długość_interwału <= teraz`.
Giełda zawsze zwraca trwającą świecę jako ostatnią — liczenie z niej wskaźników
dawałoby wartości zmieniające się w trakcie świecy.

### `pobierz_swiece_od(symbol, interwal, od, maks_swiec=5000) -> DataFrame`
**Co robi:** pobiera zamknięte świece od chwili `od` do teraz (używa symulator do rozliczania transakcji).
**Jak działa:** `fetch_ohlcv(since=...)` po 1000 świec (limit Binance) w pętli, aż do końca
danych albo `maks_swiec`; odrzuca trwającą świecę i duplikaty. Czas w UTC.

### `aktualne_ceny(symbole) -> dict`
Ostatnie ceny (`last`) dla listy par jednym zapytaniem o tickery — używane przez raport
(„kup i trzymaj” per para). Pusta lista → pusty słownik.

### `pobierz_dane(stan) -> dict` *(węzeł grafu)*
**Co robi:** pobiera ticker i historię świec dla `stan["symbol"]` / `stan["interwal"]`.
**Jak działa:**
- ticker (okno 24h): ceny, wolumen, bid/ask; liczy **spread %** = (ask − bid) / średnia;
  pomija `markPrice`/`indexPrice` (istnieją tylko na futures),
- świece: `LIMIT_SWIEC + 1` sztuk, potem odrzucenie trwającej (czas „teraz” z tickera giełdy,
  a gdy brak — z zegara),
- przy błędzie wypisuje komunikat i rzuca wyjątek dalej.

**Zwraca:** `{"aktualne_dane": {...}, "dane_historyczne": DataFrame}`.

### `_format_procent(wartosc) -> str`
Formatuje procent z 4 miejscami po przecinku albo `"brak"` dla `None`.

### `formatuj_ticker(aktualne_dane) -> str`
**Co robi:** blok danych `ticker` do promptu — ceny 24h, VWAP, zmiana, wolumen, bid/ask, spread, czas.

### `cena_wejscia(aktualne_dane) -> float`
**Co robi:** cena, po której kupilibyśmy zleceniem rynkowym.
**Jak działa:** `ask`, a gdy go brak — `last`. Używana przez traderów, Head Tradera,
Risk Managera i symulator, żeby wszyscy liczyli od tej samej ceny.

### `formatuj_swiece(swiece, interwal, liczba=SWIECE_W_PROMPCIE) -> str`
**Co robi:** blok `swiece` / `swiece_krotkie` — tabela ostatnich `liczba` zamkniętych świec (czas UTC).
