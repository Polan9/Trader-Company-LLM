# `wskazniki/` — obliczenia (bez LLM)

Definicje zgodne z TradingView. Każdy wskaźnik zweryfikowany z niezależną implementacją
referencyjną (różnica ~1e-14).

## `wskazniki/obliczenia.py` — czyste funkcje

### `_wygladz(seria, okres, alpha) -> Series`
**Co robi:** wygładzanie wykładnicze — wspólna podstawa EMA i RMA.
**Jak działa:** pomija wiodące NaN; pierwsza wartość = **SMA z pierwszych `okres` wartości**,
dalej `wynik[i] = alpha * x[i] + (1 − alpha) * wynik[i−1]`. Przed startem — NaN.

### `ema(seria, okres) -> Series`
Średnia wykładnicza: `_wygladz` z `alpha = 2 / (okres + 1)`.

### `rma(seria, okres) -> Series`
Średnia Wildera (używana w RSI i ATR): `_wygladz` z `alpha = 1 / okres`.

### `rsi(zamkniecia, okres=14) -> Series`
**Co robi:** klasyczny RSI Wildera.
**Jak działa:** zmiany cen dzielone na zyski i straty, każde wygładzone `rma`;
`RSI = 100 − 100 / (1 + średni_zysk / średnia_strata)`. Przypadki brzegowe:
same wzrosty → 100, brak ruchu → 50.

### `macd(zamkniecia, szybki=12, wolny=26, sygnal=9) -> (linia, linia_sygnalu, histogram)`
Linia = EMA(szybki) − EMA(wolny); sygnał = EMA(linii, sygnal); histogram = linia − sygnał.

### `true_range(swiece) -> Series`
Największa z: `high − low`, `|high − poprz. close|`, `|low − poprz. close|`.
Uwzględnia luki cenowe. Dla pierwszej świecy (brak poprzedniego zamknięcia) — `high − low`.

### `atr(swiece, okres=14) -> Series`
Average True Range: `rma(true_range)`. Średni zakres ruchu na świecę.

### `nachylenie_procentowe(seria) -> float`
**Co robi:** trend serii w % średniej na jedną świecę.
**Jak działa:** prosta dopasowana metodą najmniejszych kwadratów (`np.polyfit`), nachylenie / średnia × 100.
Używane do trendu wolumenu (odporniejsze niż porównanie pierwszej i ostatniej świecy).

## `wskazniki/analiza_techniczna.py`

### `oblicz_analize_techniczna(stan) -> dict` *(węzeł grafu)*
**Co robi:** liczy wszystkie wskaźniki dla ostatniej zamkniętej świecy i ich interpretację.
**Jak działa:**
- walidacja: są świece i jest ich ≥ `MIN_SWIEC`; po obliczeniu — brak NaN,
- RSI, MACD, ATR (+ ATR jako % ceny), wolumen vs poprzednia świeca i vs średnia
  z **poprzednich** 20 świec (bez bieżącej),
- trend wolumenu z `nachylenie_procentowe` (próg `PROG_TRENDU_WOLUMENU`),
- interpretacje tekstowe (strefa RSI, przecięcia MACD jako flagi True/False),
- heurystyczne sygnały wejścia/wyjścia + flaga `ma_sygnal_wejscia` (strategia odniesienia w raporcie),
- `statystyki` z `oblicz_statystyki`.
Wartości bez zaokrągleń (tanie coiny mają ceny rzędu 0.0001).

**Zwraca:** `{"analiza_techniczna": {...}}`.

### Formatery bloków danych
Każdy przyjmuje słownik `analiza_techniczna` i zwraca tekst do promptu (liczby `:.6g`):

| Funkcja | Blok | Treść |
|---|---|---|
| `formatuj_wolumen` | `wolumen` | wolumen ostatniej/poprzedniej świecy, średnia, zmiany %, trend |
| `formatuj_rsi` | `rsi` | wartość, poprzednia, strefa, interpretacja |
| `formatuj_macd` | `macd` | linia, sygnał, histogram, interpretacja |
| `formatuj_atr` | `atr` | ATR i ATR jako % ceny |
| `formatuj_sygnaly_heurystyczne` | `sygnaly_heurystyczne` | sygnały wejścia/wyjścia z prostej heurystyki |

### `formatuj_analize_techniczna(analiza) -> str`
Wszystkie powyższe bloki razem — do zapisu stanu w pliku.

## `wskazniki/statystyki.py` — blok quanta

### `oblicz_statystyki(swiece) -> dict`
**Co robi:** statystyki stóp zwrotu i położenia ceny.
**Jak działa** (zwroty = `pct_change` × 100):
- zwrot ostatniej świecy i z `OKNO_KROTKIE` świec, udział świec wzrostowych,
- zmienność = odchylenie standardowe zwrotów (okno krótkie i długie),
- **z-score ceny** = (cena − średnia 20) / odchylenie 20 — jak daleko od średniej,
- **pozycja w zakresie** 50 świec: 0 = minimum, 100 = maksimum,
- **autokorelacja** zwrotów (lag 1, 100 świec): dodatnia = ruchy się kontynuują, ujemna = odwracają.
Błąd, gdy świec mniej niż największe okno + 1.

### `formatuj_statystyki(statystyki) -> str`
Blok `statystyki` do promptu, z opisem słownym autokorelacji (próg ±0.1).
