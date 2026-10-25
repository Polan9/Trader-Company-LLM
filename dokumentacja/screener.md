# `screener/wybor.py` — wybór pary przed zwołaniem ławy

Przed każdą rundą screener wybiera **jedną** parę, o której dyskutuje ława. Cel: grać tam,
gdzie typowy ruch (ATR) najlepiej pokrywa koszty transakcji. Bez LLM — czysty kod,
ok. 10–15 s na rundę (ticker wszystkich par + świece 30 kandydatów).

## Kryteria (stałe `SCREENER_*` w `konfiguracja/ustawienia.py`)

| Krok | Kryterium | Domyślnie |
|---|---|---|
| 1 | aktywna para spot `*/USDT`, spoza `WYKLUCZONE_AKTYWA` i spoza par z otwartą pozycją | — |
| 2 | `SCREENER_LICZBA_KANDYDATOW` najpłynniejszych (wolumen 24h w USDT) | 30 |
| 3 | wolumen 24h ≥ `SCREENER_MIN_WOLUMEN_USDT` | 20 mln USDT |
| 4 | spread ≤ `SCREENER_MAKS_SPREAD_PROCENT` | 0.05% |
| 5 | mediana ATR% z `SCREENER_OKNO_ATR` świec ≥ `SCREENER_MIN_ATR_PROCENT` (odrzuca „prawie stablecoiny”) | 24 świece, 0.15% |
| 6 | koszt transakcji / ATR ≤ `SCREENER_MAKS_KOSZT_DO_ATR` | 25% |

**Ranking:** najniższy koszt/ATR (remis → większy wolumen). Wybierana jest pierwsza para.
Koszt liczony tą samą funkcją co w ławie (`koszt_transakcji_procent`: prowizje, poślizg, spread).

`WYKLUCZONE_AKTYWA` to lista ręczna — API Binance nie ma pola odróżniającego tokenizowane
akcje/złoto od kryptowalut. Gdy w rankingu pojawi się nowy taki token (np. z końcówką `B`
jak `MSTRB`), trzeba go dopisać. **Nie wykluczamy po końcówce nazwy** — `BNB`, `ARB` to zwykłe coiny.

## Funkcje

### `_kandydaci(gielda, pomin) -> list[dict]`
**Co robi:** wstępna lista par z jednego zapytania o tickery wszystkich par.
**Jak działa:** filtr z kroku 1, spread % z bid/ask, sortowanie po wolumenie 24h, pierwsze
`SCREENER_LICZBA_KANDYDATOW`. Bez pobierania świec — tanio.

### `_mediana_atr_procent(gielda, symbol, interwal) -> float | None`
**Co robi:** typowa zmienność pary w ostatniej dobie.
**Jak działa:** `SCREENER_SWIECE` zamkniętych świec, ATR (Wilder) / cena × 100, mediana
z ostatnich `SCREENER_OKNO_ATR` wartości (mediana — odporna na pojedynczą skrajną świecę).
`None`, gdy za mało świec.

### `ocen_pare(kandydat, atr_procent) -> dict`
**Co robi:** sprawdza kroki 3–6 dla jednej pary.
**Zwraca:** kandydata z dopisanymi `atr_procent`, `koszt_procent`, `koszt_do_atr`
i listą `odrzucenia` (pusta = para przechodzi; np. `["wolumen", "koszt/ATR"]`).

### `wybierz_pare(interwal, pomin=frozenset()) -> dict`
**Co robi:** pełny screener.
**Jak działa:** kandydaci → ATR dla każdego (błąd pojedynczej pary = odrzucenie
„za mało świec”, screener działa dalej) → ocena → ranking.
**Zwraca:** `{"symbol": wybrana para albo None, "ranking": [pary, które przeszły, posortowane],
"odrzucone": [pary odrzucone z powodami]}`.

### `formatuj_ranking(wynik, liczba=10) -> str`
Tekst do logu: wybrana para, liczba przechodzących/odrzuconych i czołówka rankingu
(koszt/ATR, ATR, spread, wolumen).

## Gdzie jest używany
- `symulacja/petla.py` → `wykonaj_cykl`: przed rundą, z pominięciem par z otwartą pozycją.
  Brak pary → runda zapisana jako pominięta (symbol `BRAK`). Ranking (czołówka + powody
  odrzuceń) zapisywany w `rundy.szczegoly["screener"]`.
- `main.py`: przy pojedynczej rundzie.
- Wyłączenie: `SCREENER_WLACZONY = False` → ława zawsze analizuje `SYMBOL`.
