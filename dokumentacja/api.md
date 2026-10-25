# `api/` — serwer interfejsu (FastAPI)

Uruchomienie: `.venv\Scripts\python.exe -m api` → http://127.0.0.1:8000 (UI + API).
Adres i port: `API_HOST` / `API_PORT` w konfiguracji; na Raspberry Pi `TRADER_API_HOST=0.0.0.0`
(dostęp z sieci domowej / Tailscale — **nie** wystawiać portu do internetu).

API **tylko czyta** bazę (połączenie `mode=ro`), więc nie może zmienić danych symulatora.
Gdy bazy nie ma → 503. Serwer działa niezależnie od symulatora (osobny proces).

## Endpointy

| Metoda i ścieżka | Zwraca |
|---|---|
| `GET /api/stan` | budżet, wynik %, koszt LLM, liczba rund, ostatnia świeca, otwarte pozycje |
| `GET /api/iteracje?limit=50&przed=<ms>` | lista iteracji (najnowsze pierwsze) ze skrótem rund: para, decyzja, głosy |
| `GET /api/iteracje/{id}` | pełna iteracja: ranking screenera, każda runda z analizą, tickerem, opiniami, ocenami, zużyciem LLM, pozycją; 404 gdy brak |
| `GET /api/swiece?symbol=&wokol=<ms>&godzin_przed=24` | świece pary od `godzin_przed` przed chwilą decyzji do teraz (czas w sekundach) |
| `GET /api/statystyki` | statystyki ławy i strategii odniesienia, krzywa kapitału, kup i trzymaj, karta traderów, koszt LLM dziennie |
| `GET /api/lawa` | konfiguracja traderów (id, nazwa, aktywny, fokus, model) i Head Tradera |
| `GET /docs` | automatyczna dokumentacja API (FastAPI) |
| `GET /*` | zbudowany frontend z `interfejs/dist` (jeśli istnieje) |

`id` iteracji = czas otwarcia świecy w milisekundach (bez znaków problematycznych w URL).

## `api/serwer.py`

### `aplikacja`
Obiekt FastAPI. CORS dopuszcza serwer deweloperski Vite (`localhost:5173`), tylko metoda GET.

### `do_json(wartosc) -> Any`
Rekurencyjnie zamienia NaN/inf na `None` oraz typy numpy/pandas (liczby, Timestamp, DataFrame)
na zwykłe typy Pythona — standardowy JSON nie dopuszcza NaN.

### `polaczenie_bazy()` *(zależność FastAPI)*
Otwiera połączenie tylko do odczytu na czas jednego zapytania i zamyka je po odpowiedzi; 503, gdy brak bazy.

### `stan(...)`, `iteracje(...)`, `iteracja(...)`, `swiece(...)`, `statystyki(...)`, `lawa()`
Obsługa endpointów z tabeli wyżej. `swiece` pobiera dane na żywo z Binance (`pobierz_swiece_od`);
`statystyki` liczy „kup i trzymaj” na żywo — bez dostępu do giełdy zwraca resztę statystyk.
Funkcje statystyk pochodzą z `symulacja/raport.py` (te same liczby co w raporcie tekstowym).

### `frontend(sciezka)`
Serwuje pliki z `interfejs/dist`; nieznana ścieżka → `index.html` (aplikacja jednostronicowa).
Pliki spoza katalogu `dist` nie są wydawane.

## `api/__main__.py`
Start `uvicorn` z `API_HOST` / `API_PORT`.

## `zapis/odczyt.py` — zapytania dla API

| Funkcja | Co robi |
|---|---|
| `polacz_do_odczytu(sciezka)` | połączenie SQLite w trybie `mode=ro` (bez możliwości zapisu) |
| `czas_na_ms(czas_iso)` / `ms_na_czas(ms)` | konwersja czasu świecy ↔ id iteracji |
| `_json_lub_pusty(tekst, domyslnie)` | parsuje kolumnę JSON albo zwraca wartość domyślną |
| `stan_portfela(polaczenie)` | budżet, koszt LLM, liczba rund, otwarte i zamknięte pozycje |
| `lista_iteracji(polaczenie, limit, przed_ms)` | iteracje (rundy pogrupowane po świecy) ze skrótem każdej rundy |
| `szczegoly_iteracji(polaczenie, iteracja_ms)` | pełne dane iteracji (screener, analiza, opinie, oceny, zużycie, pozycja); `None` gdy brak |
| `koszt_llm_dziennie(polaczenie)` | koszt LLM i liczba rund per dzień (UTC) |
| `krzywa_kapitalu(polaczenie)` | budżet po każdej zamkniętej pozycji, od budżetu początkowego |
