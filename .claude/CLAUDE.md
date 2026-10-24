# Trader Company — zasady projektu

Prywatny projekt jednej osoby. Zasady poniżej nie są sztywne — jeśli widzisz lepsze
rozwiązanie (architektura, narzędzia, flow), **zaproponuj zmianę**, zamiast ślepo trzymać się opisu.
Obecny `main.py` to tylko szkic, nie wzorzec do kopiowania.

## Cel projektu
System do **day tradingu** łączący obliczenia (Python/numpy/pandas) z LLM.
Decyzję podejmuje **„ława traderów”** — kilku agentów LLM o różnych osobowościach,
specjalizacjach i rolach, którzy głosują nad otwarciem pozycji.

## Docelowy flow
1. **Dane rynkowe** — pobranie tickera, świec OHLCV itp. z API giełdy (`ccxt`).
2. **Wskaźniki** — czysty Python/numpy/pandas liczy wskaźniki (RSI, MACD, wolumen, …).
   Obliczenia deterministyczne zawsze w kodzie, nigdy przez LLM.
3. **Sygnały informacyjne** — hybryda: skrypt zbiera newsy, tani LLM je ocenia
   (szczegóły w „Podjęte decyzje → Newsy”).
4. **Ława traderów** — każdy węzeł-trader dostaje **tylko dane właściwe dla swojej roli**
   (patrz „Dane dla ról”) i zwraca ustrukturyzowaną opinię:
   - głos: tylko `TAK` / `NIE` (bez `CZEKAJ` — niepewność = `NIE`)
   - uzasadnienie
   - stop-loss
   - take-profit
   - proponowana wielkość pozycji
5. **Głosowanie** — jeśli `głosy TAK > głosy NIE`, pozycja jest otwierana przez API giełdy
   (parametry SL/TP wyliczone z opinii, np. mediana — do ustalenia).
6. **Zapis** — pełny stan rundy (dane, opinie, głosy, decyzja) zapisywany do logu/pliku.

## Cele na później (backlog)
- **Screener coinów** — moduł wybierający, które coiny opłaca się danego dnia tradować.
  Ława analizuje tylko pary wskazane przez screener. Kryteria — patrz
  „Podjęte decyzje → Interwał i koszty”.
- **Baza danych** — stan rund, decyzje, głosy każdego tradera i wynik transakcji
  (zysk/strata) do analizy skuteczności. Rodzaj bazy do ustalenia. Do tego czasu
  wynik zapisywany do pliku `trading_state.txt`.
- **Logika wyjścia z pozycji** — SL/TP na giełdzie czy w kodzie, zachowanie ławy przy
  otwartej pozycji, limit pozycji, stan przetrwający restart. Na razie odłożona.
- **UI (po angielsku)** — m.in. definiowanie ról traderów i zakresu danych, jakie dostają.
- Futures / short i ewentualnie akcje.

## Otwarte kwestie (do ustalenia z użytkownikiem)
- Rodzaj bazy danych.
- Działanie screenera coinów (częstotliwość, liczba par, kryteria dodatkowe np. siła trendu).

## Podjęte decyzje

### Interwał i koszty (analiza: `analizy/atr_vs_koszty.py`, 2026-10-24)
- **Bazowy interwał: 1h.** Pozycje trwające kilka godzin — nadal day trading.
- Koszt transakcji = 2 × prowizja (0.1% na stronę, 0.075% z BNB) + spread.
  Opłacalność mierzymy stosunkiem **koszt / ATR** na danym interwale
  (przy SL = 1×ATR i TP = 1.5×ATR bez kosztów wystarcza 40% skuteczności).
- Wyniki (mediana z 30 najpłynniejszych par USDT, Binance spot):

  | Interwał | ATR | koszt / ATR | wymagana skuteczność |
  |---|---|---|---|
  | 5m | 0.25% | 88% | 75% — odpada |
  | 15m | 0.46% | 49% | 60% — tylko bardzo zmienne alty, na granicy |
  | 1h | 0.95% | 23% | 49% — wybrany |
  | 4h | 2.10% | 11% | 44% — to już swing trading |

  BTC/ETH/BNB na 15m wymagają 65–79% skuteczności — nieopłacalne.
- **Kryteria screenera (twarde, w kodzie):**
  - `koszt / ATR` na bazowym interwale **< 20–25%** (wartość progu w konfiguracji),
  - tylko aktywne pary spot `*/USDT`, wykluczone: stablecoiny i coiny zachowujące się jak
    stablecoin (ATR% bliski zera), tokenizowane złoto/akcje/ETF-y (np. XAUT, `*B` typu SOXLB),
  - minimalny wolumen 24h i maksymalny spread (wartości w konfiguracji).
- Prowizje w BNB włączyć przed handlem realnymi środkami (~25% taniej).
  Zlecenia limit nie obniżają prowizji na zwykłym koncie, ale omijają spread.
- Wynik analizy jest warunkiem koniecznym, nie gwarancją zysku — ATR mówi o wielkości
  ruchu, nie o trafności kierunku. Poślizg nie jest uwzględniony.

### Newsy (hybryda: skrypt + tani LLM)
- **Skrypt zbiera**: RSS portali crypto (np. Cointelegraph, Decrypt, The Block),
  Fear & Greed Index (alternative.me), dane z giełdy (funding rate, open interest, ogłoszenia).
  Deduplikacja i filtrowanie pod daną parę — w kodzie.
- **Tani LLM ocenia** paczkę nowych nagłówków jednym wywołaniem (`gpt-6-luna`),
  zwraca strukturę `pydantic`: sentyment, wpływ na cenę, pilność, krótkie streszczenie.
- Surowe nagłówki **i** ocena zapisywane z timestampem — umożliwia backtesting.
- Wynik trafia do stanu i do Analityka newsów w ławie.
- **X / Twitter — etap 2**: tylko wybrana lista kont, twardy limit wydatków
  (pay-per-use, ok. $0.005 za odczytany post — przy częstym odpytywaniu drogo).
- Pełny agent z wyszukiwaniem w sieci — nie w pętli głównej (drogi, wolny, niepowtarzalny);
  ewentualnie później jako Researcher wołany tylko w sytuacjach wyjątkowych.

### Rynek
- **Crypto, spot, tylko long**, giełda Binance przez `ccxt` (testnet dostępny).
  Głos `TAK` = kupujemy, `NIE` = nie otwieramy pozycji.
- Warstwa giełdy pisana jako wymienna (adapter), żeby później dodać futures/short
  albo akcje (np. Alpaca) bez przepisywania traderów.

### Głosowanie
- Tylko `TAK` / `NIE` — bez `CZEKAJ`, niepewność = `NIE`.
- Docelowo głosuje 5 traderów (nieparzyście → brak remisów). Pozycja otwierana, gdy `TAK > NIE`
  **i** Risk Manager nie zgłosi weta. Remis = `NIE`.
- Do czasu modułu newsów Analityk newsów ma `aktywny: false` → głosuje 4 traderów,
  więc do wejścia potrzeba min. 3 głosów TAK.
- Awaria modelu tradera lub głos `TAK` łamiący reguły SL/TP → liczony jako `NIE` (z uwagą w opinii).
- Traderzy działają równolegle (fan-out w LangGraph) i **nie widzą swoich głosów** — brak owczego pędu.

### SL / TP / wielkość pozycji (hybryda)
1. Kod liczy medianę oraz min–max SL/TP z opinii traderów głosujących `TAK`.
2. Head Trader wybiera konkretne SL/TP **w tym zakresie** i uzasadnia wybór.
3. Kod waliduje: SL obowiązkowy, stosunek zysk/ryzyko ≥ 1.5, odległość SL w granicach
   wyznaczonych z ATR. Błąd / brak odpowiedzi Head Tradera → fallback na medianę.
4. Wielkość pozycji liczy **kod**: ryzyko na transakcję (np. 1% budżetu) / odległość do SL.
   Traderzy mogą ją co najwyżej zmniejszyć.

### Dane dla ról
- Każda rola dostaje **wyłącznie dane potrzebne do swojej specjalizacji** (np. scalper:
  bid/ask, spread, ostatnie świece; analityk newsów: oceny newsów i sentyment; quant:
  statystyki i zmienność). Mniej szumu, bardziej niezależne głosy, krótsze i tańsze prompty.
- **Projektować pod przyszłe UI**: rola tradera i lista jego źródeł danych to **konfiguracja**
  (dane, nie kod) — np. `zakres_danych: ["ticker", "swiece", "rsi", "macd", ...]`.
  Każdy blok danych ma własną funkcję formatującą, a prompt tradera składany jest
  z bloków wskazanych w jego konfiguracji. Dodanie/zmiana roli nie może wymagać
  zmiany kodu węzłów.
- Role, osobowości, modele i zakres danych: **`konfiguracja/lawa.json`**.
  Dostępne bloki (`lawa/bloki_danych.py`): `ticker`, `swiece`, `swiece_krotkie`, `wolumen`,
  `rsi`, `macd`, `atr`, `sygnaly_heurystyczne`, `statystyki`, `newsy` (na razie pusty).
  Nieznana nazwa bloku = błąd przy budowie grafu.

### Koszty transakcji — ruchoma liczba
- **Wszystkie rachunki SL/TP i wielkości pozycji są po kosztach**:
  zysk netto = TP − cena − koszt, ryzyko netto = cena − SL + koszt, wymóg netto ≥ 1.5.
- Koszt = 2 × (prowizja + poślizg) + spread. Obecne wartości to **założenia, nie pomiary**:
  | Składnik | Wartość | Źródło | Pewność |
  |---|---|---|---|
  | Prowizja | 0.10% / stronę | standardowa stawka Binance spot (ccxt: taker = maker = 0.001) | wysoka, ale stawka konta może być inna (BNB, VIP) |
  | Spread | mierzony na żywo | bid/ask z tickera w każdej rundzie | wysoka dla chwili pomiaru |
  | Poślizg | 0.01% / stronę | szacunek dla płynnych par i małych zleceń | **niska** |
  | Koszt LLM | ~$0.25–0.5 / dzień | szacunek z cennika i długości promptów | **niska** |
- **Po żywym teście (testnet / realne zlecenia) skalibrować**: prowizję odczytać z konta
  (`fetch_trading_fee` z kluczem API), poślizg policzyć jako różnicę ceny zlecenia
  i ceny wykonania, koszt LLM z `usage` w odpowiedziach API. Do tego czasu traktować
  wyniki jako przybliżenie.

### Limity Risk Managera (`konfiguracja/ustawienia.py`)
- Ryzyko na transakcję 1% budżetu (strata przy SL **z kosztami**), maks. pozycja 25% budżetu,
  min. pozycja 10 USD, maks. dzienna strata 3%, maks. 5 transakcji dziennie.
- SL w odległości 0.5–3 × ATR, zysk/ryzyko **po kosztach** ≥ 1.5 — te same reguły
  (z wyliczonym minimalnym TP) trafiają do promptów.
- Minimalna pozycja 10 USD (własny próg; Binance wymaga min. 5 USDT dla BTC/USDT).
- Przy BTC na 1h limit 25% budżetu zwykle wiąże przed limitem ryzyka (faktyczne ryzyko
  ok. 0.2% budżetu) — świadomie ostrożnie na start.
- Liczniki dzienne (`dzienna_strata_procent`, `transakcje_dzisiaj`) są w stanie, ale do czasu
  bazy danych zawsze startują od zera.

### Skład ławy (wzór: firma prop tradingowa)
Modele trzymane w konfiguracji tradera (łatwa podmiana). Mieszanka rodzin modeli celowo —
różne modele mylą się inaczej. Ceny OpenAI (wejście / wyjście za 1M tokenów, stan 2026-10).

| Rola | Osobowość / fokus | Głos | Model | Cena |
|---|---|---|---|---|
| Trend / momentum trader | pewny siebie, gra z trendem; MACD, średnie, wybicia | tak | `gpt-6-luna` | $0.10 / $0.50 |
| Scalper / price action | szybki, krótki horyzont; bid/ask, wolumen ostatnich świec | tak | `gpt-5-nano` | $0.05 / $0.40 |
| Contrarian (mean reversion) | sceptyk, adwokat diabła; RSI skrajne, przesadzone ruchy | tak | `gpt-4.1-mini` | $0.40 / $1.60 |
| Analityk newsów i sentymentu | czyta rynek przez wydarzenia; newsy, X, makro | tak | `gpt-5.6-luna` | $0.20 / $1.20 |
| Quant | chłodny, liczby; zmienność, statystyka, oczekiwany zysk | tak | `gpt-5-mini` | $0.25 / $2.00 |
| Head Trader (szef desku) | agreguje opinie, ustala SL/TP; wołany tylko gdy `TAK > NIE` | nie | `gpt-6.1-sol` | $2.00 / $10.00 |
| Risk Manager | twarde limity w kodzie, **weto**; opcjonalny komentarz LLM | weto | kod (+ `gpt-6-luna`) | ~0 |
| Researcher | skrypt zbiera newsy, LLM ocenia (krok 3 flow) | nie | skrypt + `gpt-6-luna` | ~$0.05/dzień |
| Execution | składa zlecenia przez API giełdy | nie | kod | 0 |

- Szacunkowy koszt przy interwale 1h (24 rundy/dzień, jedna para): ok. $0.25–0.5 dziennie
  (ława ~ułamek centa na rundę, Head Trader ~$0.02 za wywołanie). Koszt rośnie
  liniowo z liczbą par wskazanych przez screener.
- Uwaga: modele rozumujące (rodzina gpt-5/gpt-6) liczą tokeny rozumowania jako wyjście
  i mogą nie wspierać `temperature` — używać niskiego `reasoning_effort`, sprawdzić
  obsługiwane parametry przed użyciem. `gpt-4.1-mini` wspiera `temperature=0`.

## Język
- **Kod po polsku**: nazwy zmiennych, funkcji, klas, węzłów grafu, pól stanu,
  komentarze, docstringi, komunikaty `print`/błędów, prompty LLM.
- **Identyfikatory bez polskich znaków** (`gielda`, nie `giełda`) — polskie znaki
  dozwolone w stringach, komentarzach i promptach.
- Wyjątki: nazwy z bibliotek i API giełdy zostają oryginalne (`fetch_ohlcv`, `'close'`,
  `'baseVolume'`), standardowe skróty wskaźników też (`rsi`, `macd`, `vwap`).
- **UI po angielsku** (etap późniejszy — na razie brak UI).

## Konwencje kodu
- `snake_case` dla funkcji i zmiennych, `PascalCase` dla klas, `WIELKIE_LITERY` dla stałych
  konfiguracyjnych (np. `SYMBOL`, `INTERWAL`).
- Funkcje pomocnicze prywatne z prefiksem `_`.
- Type hints wszędzie; stan grafu jako `TypedDict`, ustrukturyzowane odpowiedzi LLM
  jako modele `pydantic` (`with_structured_output`) zamiast parsowania tekstu.
- Węzeł grafu: przyjmuje stan, zwraca **słownik tylko ze zmienionymi polami**.
- Walidacja wejścia na początku węzła; przy braku danych `raise RuntimeError` z opisem po polsku.
- Jeden trader = jedna konfiguracja (nazwa, osobowość, prompt systemowy, model) —
  traderzy budowani z tej samej funkcji fabrykującej, nie kopiowany kod.
- Funkcje używane między modułami są publiczne (bez `_`); `_` tylko dla pomocniczych wewnątrz modułu.
- Klienci LLM tworzeni leniwie (przy pierwszym użyciu), żeby import modułu nie wymagał klucza API.

## Struktura kodu
```
main.py                     # tylko składa graf LangGraph i uruchamia rundę
stan.py                     # AktualnyStan (TypedDict) — wspólny stan grafu
konfiguracja/ustawienia.py  # stałe: ścieżki, rynek, świece, okresy wskaźników, modele
dane/gielda.py              # pobieranie z giełdy (ccxt) + formatery bloków: ticker, świece
wskazniki/obliczenia.py     # czyste funkcje: ema, rma, rsi, macd, true_range, atr, ...
wskazniki/analiza_techniczna.py  # węzeł analizy technicznej + formater bloku
konfiguracja/lawa.json      # role traderów i Head Tradera (dane, docelowo edytowane z UI)
konfiguracja/lawa.py        # wczytanie i walidacja lawa.json (pydantic)
wskazniki/statystyki.py     # statystyki zwrotów (blok danych quanta)
lawa/bloki_danych.py        # rejestr bloków danych → składanie promptu tradera
lawa/traderzy.py            # fabryka węzłów-traderów z konfiguracji
lawa/glosowanie.py          # liczenie głosów, mediana/zakres SL/TP, krawędź warunkowa
lawa/head_trader.py         # wybór SL/TP z zakresu ławy, fallback na medianę
lawa/risk_manager.py        # weto + wielkość pozycji
lawa/sl_tp.py               # twarde reguły SL/TP i wyliczanie wielkości pozycji
lawa/modele.py              # schematy odpowiedzi LLM (pydantic)
lawa/llm.py                 # jedyne miejsce wywołań LLM (łatwe podmienienie w testach)
zapis/plik_stanu.py         # zapis rundy do pliku (tymczasowo, docelowo baza danych)
analizy/                    # jednorazowe analizy (uruchamiane: python -m analizy.<nazwa>)
```
- Nowe obszary jako kolejne pakiety, np. `sygnaly/` (newsy), `screener/`, `wykonanie/` (zlecenia).
- Każdy blok danych dla promptu ma funkcję `formatuj_<blok>` obok kodu, który te dane tworzy.
- Uruchamianie zawsze z katalogu głównego (`python main.py`) — importy są absolutne od korzenia projektu.

## Prompty LLM
- Po polsku, z jasno określonym formatem odpowiedzi.
- Powtarzalność decyzji: `temperature=0` tam, gdzie model to wspiera; w modelach
  rozumujących niski `reasoning_effort` (patrz tabela ławy).
- Dane formatowane funkcjami pomocniczymi (jak `formatuj_analize_techniczna`),
  nie surowe struktury.

## Bezpieczeństwo i wykonywanie zleceń
- Kolejność wdrażania: **symulacja (paper trading) → testnet giełdy → realne środki**.
  Przejście na realne środki tylko na wyraźną decyzję użytkownika.
- Twarde zabezpieczenia w kodzie, nie w promptach: maks. wielkość pozycji, maks. dzienna strata,
  obowiązkowy stop-loss, walidacja odpowiedzi LLM przed wysłaniem zlecenia.
- Tryb (symulacja/testnet/realny) jako jawny przełącznik w konfiguracji, domyślnie symulacja.
- Klucze API tylko w `.env` + `load_dotenv()`, nigdy w kodzie ani w logach.
  **Nie czytaj, nie wypisuj i nie modyfikuj `.env`.**

## Dokładność obliczeń
- Wskaźniki liczone **tylko z zamkniętych świec** — trwającą świecę (ostatnią z `fetch_ohlcv`) odrzucamy.
- Standardowe definicje zgodne z TradingView: RSI z wygładzaniem Wildera (RMA), EMA ze startem od SMA.
- Pobieramy zapas świec na rozgrzewkę wskaźników (`LIMIT_SWIEC`), walidujemy brak NaN.
- Wartości przechowywane bez zaokrągleń; zaokrąglanie tylko przy formatowaniu
  (cyfry znaczące, `:.6g`) — tanie coiny mają ceny rzędu 0.0001.
- Czas zawsze w UTC (`utc=True`).
- Nowy wskaźnik = weryfikacja z niezależną implementacją referencyjną przed użyciem.

## Środowisko
- Python 3.12, wirtualne środowisko `.venv` w katalogu głównym (tylko pakiety, bez kodu).
- Kod w katalogu głównym, repozytorium git (`.gitignore`: `.env`, `.venv/`, `.idea/`, `trading_state.*`).
- Uruchamianie: `.venv\Scripts\python.exe main.py`
- Pakiety tylko do `.venv`: `.venv\Scripts\pip.exe install <pakiet>`
- `.env` w katalogu głównym, ładowany jawną ścieżką (`KATALOG_PROJEKTU / ".env"`).
