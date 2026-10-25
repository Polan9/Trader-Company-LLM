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
- **Logika wyjścia z pozycji (pełna)** — na razie wersja minimalna w symulatorze
  (SL / TP / zamknięcie po `MAKS_CZAS_POZYCJI_SWIEC`, maks. `MAKS_OTWARTYCH_POZYCJI`
  otwartych pozycji, ława nie zbiera się po osiągnięciu limitu). Do ustalenia: wcześniejsze wyjście decyzją ławy,
  trailing stop, SL/TP jako zlecenia OCO na giełdzie (przy trybie testnet/realny).
- **UI — kolejne etapy** (etap 1 gotowy, patrz „Interfejs”): etap 2 — biuro 3D (lepsze modele,
  pokoje, przepływ danych), etap 3 — wykresy w statystykach, etap 4 — animacje postaci,
  odświeżanie na żywo, edycja ról i zakresu danych z UI, logowanie.
- Futures / short i ewentualnie akcje.

## Otwarte kwestie (do ustalenia z użytkownikiem)
- Screener: czy dodać kryteria jakościowe (siła trendu, korelacja z BTC) i czy dopuścić
  kilka otwartych pozycji naraz (`MAKS_OTWARTYCH_POZYCJI` > 1 — crypto są mocno skorelowane).

## Podjęte decyzje

### Interfejs (decyzja 2026-10-25; opis kodu: `dokumentacja/api.md`, `dokumentacja/interfejs.md`)
- **W przeglądarce**, dostępny z różnych urządzeń (telefon, tablet, komputer) — układ responsywny.
- Stos: **FastAPI** (Python, `api/`) — API tylko do odczytu + serwowanie zbudowanego frontendu;
  **React + TypeScript + Vite** (`interfejs/`), **react-three-fiber + drei** (biuro 3D),
  **lightweight-charts** (świece). Na Pi jeden proces (`python -m api`), Node.js tylko do budowania.
- API czyta bazę w trybie `mode=ro` — interfejs nie może zmienić danych symulatora.
- Dostęp: domyślnie `127.0.0.1`; na Pi `TRADER_API_HOST=0.0.0.0` w sieci domowej, spoza domu
  przez **Tailscale**. **Nie wystawiać portu do internetu.** Logowanie — etap 4.
- Zakładki: **Preview** — latająca makieta biura 3D (obrót, przybliżenie): duży kwadratowy pokój
  z owalnym stołem i miejscem dla każdego tradera, po prawej gabinet Head Tradera i pokój
  pozostałych (Risk Manager, Screener, Researcher, Execution); w przyszłości animacje postaci
  i wizualizacja tego, co dzieje się w kodzie. **Reports** — raport każdej iteracji z podglądem
  (ranking screenera, wykres świec z poziomami, opinie, oceny). **Statistics** — statystyki.
- Napisy UI po angielsku; dane z systemu (uzasadnienia LLM, interpretacje) zostają po polsku.
- Wersje pakietów npm przypięte dokładnie w `interfejs/package.json`.

### Screener (`screener/wybor.py`, opis: `dokumentacja/screener.md`)
- **Przed każdą rundą** screener wybiera **jedną** parę, o której dyskutuje ława. Kod, bez LLM.
- Kryteria twarde: kandydaci = 30 najpłynniejszych `*/USDT` spoza `WYKLUCZONE_AKTYWA`
  i spoza par z otwartą pozycją; wolumen ≥ 20 mln USDT, spread ≤ 0.05%, mediana ATR% (doba)
  ≥ 0.15%, koszt/ATR ≤ 25%. Ranking: najniższy koszt/ATR.
- `WYKLUCZONE_AKTYWA` — ręczna lista (API nie odróżnia tokenizowanych akcji/złota);
  **nie wykluczać po końcówce nazwy** (`BNB`, `ARB` to zwykłe coiny).
- Pierwszy pomiar (2026-10-25, niedziela): przeszło 5 z 30 par (WLD, ZEC, NEAR, ENA, SUI);
  BTC odpadł (koszt/ATR 59%), ETH/SOL/XRP ~33–35%.
- Maks. `MAKS_OTWARTYCH_POZYCJI = 1` łącznie.
- **Przeszukiwanie rynku (decyzja 2026-10-25):** gdy ława powie NIE, analizuje kolejną parę
  z rankingu — do otwarcia pozycji albo `MAKS_PAR_NA_SWIECE = 4` par. Cel: przejrzeć więcej
  rynku, **nie** wymusić wejście — nigdy nie pytamy ponownie o tę samą parę (to byłoby
  losowanie odpowiedzi LLM aż do TAK). Koszt LLM do ~4× wyższy (ok. $0.016 / świecę zamiast $0.004).
- **Decyzja użytkownika (2026-10-25): bez limitu maksymalnego ATR** — coiny po nagłym wzroście
  zostają (okazja na wejście), a przy nagłym spadku ława i tak głosuje NIE. Ranking po
  najniższym koszt/ATR będzie więc często wybierał najbardziej zmienne pary (np. BMT, ATR ~10%/h).
  Do obserwacji w raporcie: wyniki na takich parach i realny poślizg (założenie 0.01% jest
  optymistyczne dla płytkich rynków). Wrócić do tematu, jeśli dane pokażą problem.

### Platforma i baza danych
- **Docelowo system działa na Raspberry Pi** (4 lub 5, 4 GB RAM wystarczy — ciężka praca
  LLM odbywa się w chmurze). Wszystkie zależności muszą działać na ARM64 (aarch64);
  nowe biblioteki sprawdzać pod tym kątem.
- **Baza: SQLite** w trybie WAL (`PRAGMA journal_mode=WAL`) — zero dodatkowych usług,
  obciążenie znikome (kilkadziesiąt–kilkaset wierszy na dobę), równoległy odczyt dla przyszłego UI.
- Cały dostęp do bazy **tylko przez warstwę w `zapis/`** — reszta kodu nie zna silnika bazy.
  Przejście na PostgreSQL rozważyć dopiero, gdy: kilka niezależnych procesów zapisuje
  jednocześnie, baza ma być dostępna przez sieć albo danych będzie bardzo dużo.
- Wymagania wdrożenia na Pi:
  - baza i logi na **dysku SSD (USB)**, nie na karcie SD (zużycie, ryzyko uszkodzenia
    przy utracie zasilania); najlepiej cały system uruchamiany z SSD,
  - **codzienna kopia bazy** na inny nośnik / do chmury (bezpieczna kopia SQLite w trakcie działania),
  - **synchronizacja czasu (NTP)** — Pi nie ma podtrzymywanego zegara, a odrzucanie
    niezamkniętych świec opiera się na czasie,
  - uruchamianie jako **usługa systemd** (autostart, restart po awarii),
  - opcjonalnie UPS — zalecany przed handlem realnymi środkami.
- Ścieżki (baza, logi) w konfiguracji, żeby na Pi wskazać katalog na SSD.

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
  bid/ask, spread, ostatnie świece; analityk newsów: oceny newsów i sentyment; statystyk:
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
  | Koszt LLM | $0.0038 / rundę (4 traderzy, bez Head Tradera) | **pomiar** z `usage_metadata`, 1 runda 2026-10-24 | średnia — jedna próbka |
- **Po żywym teście (testnet / realne zlecenia) skalibrować**: prowizję odczytać z konta
  (`fetch_trading_fee` z kluczem API), poślizg policzyć jako różnicę ceny zlecenia
  i ceny wykonania. Koszt LLM liczony automatycznie w każdej rundzie (`lawa/llm.py`,
  ceny w `CENNIK_MODELI` — aktualizować ręcznie). Do tego czasu traktować
  wyniki jako przybliżenie.

### Limity Risk Managera (`konfiguracja/ustawienia.py`)
- Ryzyko na transakcję 1% budżetu (strata przy SL **z kosztami**), maks. pozycja 25% budżetu,
  min. pozycja 10 USD, maks. dzienna strata 3%, maks. 5 transakcji dziennie.
- SL w odległości 0.5–3 × ATR, zysk/ryzyko **po kosztach** ≥ 1.5 (tolerancja 0.01 na
  zaokrąglenia cen przez LLM) — te same reguły (z wyliczonym minimalnym TP) trafiają do promptów.
- Skala pozycji od tradera (0–100) to część pełnej pozycji wyliczonej przez Risk Managera,
  nie procent budżetu.
- Minimalna pozycja 10 USD (własny próg; Binance wymaga min. 5 USDT dla BTC/USDT).
- Przy BTC na 1h limit 25% budżetu zwykle wiąże przed limitem ryzyka (faktyczne ryzyko
  ok. 0.2% budżetu) — świadomie ostrożnie na start.
- Liczniki dzienne (`dzienna_strata_procent`, `transakcje_dzisiaj`) liczone z bazy przez
  symulator (doba UTC); w pojedynczej rundzie `main.py` startują od zera.

### Symulator (`python -m symulacja`, raport: `python -m symulacja.raport`)
- Cykl co godzinę po zamknięciu świecy: rozliczenie otwartych → (jeśli limit otwartych
  pozycji nie osiągnięty) screener → rundy ławy dla kolejnych par z rankingu → zapis w SQLite.
  Restart w tej samej godzinie nie powtarza przeszukiwania ani kosztów LLM.
- Wejście w świecy **po** decyzji, po cenie `ask`. Rozstrzyganie konserwatywne: luka pod SL →
  wyjście po otwarciu; SL i TP w jednej świecy → świece 1m, remis → SL.
- **Oceny (transakcje hipotetyczne)**: referencja w każdej rundzie (SL 1×ATR, minimalny TP)
  i każdy głos TAK na własnych poziomach. Karta traderów: TAK trafny = własna transakcja
  na plus, NIE trafny = referencja na minus.
- Raport porównuje ławę ze strategiami odniesienia: „zawsze wchodź”, „heurystyka RSI/MACD”,
  „kup i trzymaj BTC” (benchmark rynku) i „kup i trzymaj pary” (per para od pierwszej rundy
  na niej, po kosztach) — screener wybiera różne coiny, więc cen różnych par nie porównujemy. Poniżej ~100 zamkniętych transakcji wyniki traktować jako niemiarodajne.

### Skład ławy (wzór: firma prop tradingowa)
Modele trzymane w konfiguracji tradera (łatwa podmiana). Mieszanka rodzin modeli celowo —
różne modele mylą się inaczej. Ceny OpenAI (wejście / wyjście za 1M tokenów, stan 2026-10).

| Rola | Osobowość / fokus | Głos | Model | Cena |
|---|---|---|---|---|
| Trend / momentum trader | pewny siebie, gra z trendem; MACD, średnie, wybicia | tak | `gpt-6-luna` | $0.10 / $0.50 |
| Scalper / price action | szybki, krótki horyzont; bid/ask, wolumen ostatnich świec | tak | `gpt-5-nano` | $0.05 / $0.40 |
| Łowca odbić (`lowca_odbic`, dawniej Contrarian) | sceptyk, adwokat diabła; gra na powrót ceny do średniej po przesadzonym ruchu; RSI skrajne | tak | `gpt-4.1-mini` | $0.40 / $1.60 |
| Analityk newsów i sentymentu | czyta rynek przez wydarzenia; newsy, X, makro | tak | `gpt-5.6-luna` | $0.20 / $1.20 |
| Statystyk (`statystyk`, dawniej Quant) | chłodny, liczby; zmienność, statystyka, oczekiwany zysk | tak | `gpt-5-mini` | $0.25 / $2.00 |
| Head Trader (szef desku) | agreguje opinie, ustala SL/TP; wołany tylko gdy `TAK > NIE` | nie | `gpt-6.1-sol` | $2.00 / $10.00 |
| Risk Manager | twarde limity w kodzie, **weto**; opcjonalny komentarz LLM | weto | kod (+ `gpt-6-luna`) | ~0 |
| Researcher | skrypt zbiera newsy, LLM ocenia (krok 3 flow) | nie | skrypt + `gpt-6-luna` | ~$0.05/dzień |
| Execution | składa zlecenia przez API giełdy | nie | kod | 0 |

- Zmierzony koszt (2026-10-24, 1 runda): ława 4 traderów **$0.0038 / rundę**; przy 1h
  (24 rundy/dzień, jedna para) ok. **$0.09 dziennie, ~$2.7 miesięcznie** + Head Trader
  (szacunek ~$0.01 za wywołanie, tylko przy TAK). Wcześniejszy szacunek ($0.25–0.5/dzień)
  był 3–5× zawyżony. Koszt rośnie liniowo z liczbą przeszukiwanych par: przy
  `MAKS_PAR_NA_SWIECE = 4` i samych NIE do ok. $0.38 dziennie (~$11.5 miesięcznie).
  Próg opłacalności przy ~$9–11.5 / mies. (R ≈ 0.5% budżetu na zmiennych altach, ~20 transakcji/mies.):
  ok. 720 USD przy skuteczności 45%, 360 USD przy 50%, 240 USD przy 55%; przy ≤ 40% — nigdy.
  Najdroższe na rundę: gpt-5-mini i gpt-4.1-mini; gpt-5-nano zużywa dużo tokenów rozumowania.
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
wskazniki/statystyki.py     # statystyki zwrotów (blok danych statystyka)
lawa/bloki_danych.py        # rejestr bloków danych → składanie promptu tradera
lawa/traderzy.py            # fabryka węzłów-traderów z konfiguracji
lawa/glosowanie.py          # liczenie głosów, mediana/zakres SL/TP, krawędź warunkowa
lawa/head_trader.py         # wybór SL/TP z zakresu ławy, fallback na medianę
lawa/risk_manager.py        # weto + wielkość pozycji
lawa/sl_tp.py               # twarde reguły SL/TP i wyliczanie wielkości pozycji
lawa/modele.py              # schematy odpowiedzi LLM (pydantic)
lawa/llm.py                 # jedyne miejsce wywołań LLM (łatwe podmienienie w testach)
screener/wybor.py           # wybór pary przed rundą (koszt/ATR, wolumen, spread)
zapis/baza.py               # SQLite (WAL) — jedyne miejsce znające silnik bazy
zapis/odczyt.py             # zapytania tylko do odczytu dla API
zapis/plik_stanu.py         # czytelny podgląd ostatniej rundy (trading_state.txt)
api/serwer.py               # FastAPI: endpointy /api/* + serwowanie interfejs/dist
api/__main__.py             # python -m api
interfejs/                  # frontend (React + TypeScript + Vite), src/zakladki/: Podglad, Raporty, Statystyki
symulacja/petla.py          # pętla symulatora: rozliczenie → runda → zapis
symulacja/ocena.py          # rozstrzyganie SL/TP/czas na świecach, wynik netto w R
symulacja/raport.py         # raport skuteczności i karta traderów
symulacja/__main__.py       # python -m symulacja [--raz]
analizy/                    # jednorazowe analizy (uruchamiane: python -m analizy.<nazwa>)
dokumentacja/               # opis każdej funkcji: co robi i jak działa
```
- **Dokumentacja (`dokumentacja/`) aktualizowana razem z kodem**: każda nowa lub zmieniona
  funkcja/klasa = wpis w pliku dokumentacji jej pakietu (co robi, jak działa, co zwraca).
  Zmiana kodu bez aktualizacji dokumentacji jest niekompletna.
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
- Uruchamianie: `.venv\Scripts\python.exe main.py` (jedna runda),
  `.venv\Scripts\python.exe -m symulacja` (symulator), `-m symulacja.raport` (raport).
- Baza i logi w `dane_lokalne/` (ignorowane przez git); inny katalog przez zmienną
  środowiskową `TRADER_KATALOG_DANYCH`.
- Zależności Pythona: `requirements.txt` (pip freeze; `winloop` tylko na Windows).
  Nowy pakiet = dopisać do `requirements.txt` i sprawdzić dostępność na ARM64.
- Interfejs: `.venv\Scripts\python.exe -m api` → http://127.0.0.1:8000. Po zmianach
  w `interfejs/src`: `npm run build` w `interfejs/` (Node.js: `C:\Program Files\nodejs`,
  może nie być w PATH powłoki Claude — dodać `export PATH="/c/Program Files/nodejs:$PATH"`).
  `interfejs/node_modules` i `interfejs/dist` ignorowane przez git.
- Symulator i serwer interfejsu to **osobne procesy** — restart jednego nie wpływa na drugi.
- Pakiety tylko do `.venv`: `.venv\Scripts\pip.exe install <pakiet>`
- `.env` w katalogu głównym, ładowany jawną ścieżką (`KATALOG_PROJEKTU / ".env"`).
