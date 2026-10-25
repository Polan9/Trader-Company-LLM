import os
from pathlib import Path

# --- Ścieżki ---
KATALOG_PROJEKTU = Path(__file__).resolve().parent.parent
PLIK_ENV = KATALOG_PROJEKTU / ".env"
PLIK_STANU = KATALOG_PROJEKTU / "trading_state.txt"
PLIK_KONFIGURACJI_LAWY = KATALOG_PROJEKTU / "konfiguracja" / "lawa.json"
# Baza i logi — na Raspberry Pi wskazać katalog na SSD zmienną środowiskową
# TRADER_KATALOG_DANYCH (np. w pliku usługi systemd: Environment=...).
KATALOG_DANYCH = Path(os.environ.get("TRADER_KATALOG_DANYCH", KATALOG_PROJEKTU / "dane_lokalne"))
PLIK_BAZY = KATALOG_DANYCH / "trader.db"
KATALOG_LOGOW = KATALOG_DANYCH / "logi"

# --- Interfejs (API) ---
# Domyślnie tylko ten komputer; na Raspberry Pi ustawić TRADER_API_HOST=0.0.0.0 (dostęp z sieci
# domowej / Tailscale). Nie wystawiać portu do internetu.
API_HOST = os.environ.get("TRADER_API_HOST", "127.0.0.1")
API_PORT = int(os.environ.get("TRADER_API_PORT", "8000"))
KATALOG_INTERFEJSU = KATALOG_PROJEKTU / "interfejs" / "dist"  # zbudowany frontend (npm run build)

# --- Tryb ---
TRYB = "symulacja"  # symulacja | testnet | realny — zlecenia jeszcze nie są składane

# --- Rynek ---
SYMBOL = "BTC/USDT"
INTERWAL = "1h"  # na 5m/15m prowizje zjadają 50–90% ATR — patrz analizy/atr_vs_koszty.py
BUDZET_POCZATKOWY = 1000.0
# Koszty transakcji to założenia — ruchoma liczba, do skalibrowania na podstawie
# rzeczywistych transakcji (testnet / żywy test). Spread mierzony na żywo w każdej rundzie.
PROWIZJA_STRONA_PROCENT = 0.10  # Binance spot, standardowa stawka taker bez zniżki BNB
POSLIZG_STRONA_PROCENT = 0.01  # szacunek dla zleceń rynkowych na płynnych parach

# --- Zarządzanie ryzykiem (twarde limity Risk Managera) ---
RYZYKO_NA_TRANSAKCJE_PROCENT = 1.0  # % budżetu tracony przy trafieniu SL (z kosztami)
MAKS_POZYCJA_PROCENT_BUDZETU = 25.0
MIN_WIELKOSC_POZYCJI_USD = 10.0  # minimalna wartość zlecenia na Binance
MAKS_DZIENNA_STRATA_PROCENT = 3.0
MAKS_TRANSAKCJI_DZIENNIE = 5
MIN_ZYSK_DO_RYZYKA = 1.5
TOLERANCJA_ZYSK_DO_RYZYKA = 0.01  # zaokrąglenia cen przez LLM — 1.495 przechodzi, 1.489 nie
MIN_SL_ATR = 0.5  # odległość SL od ceny wejścia, w wielokrotnościach ATR
MAKS_SL_ATR = 3.0

# --- Screener (wybór pary przed zwołaniem ławy) ---
SCREENER_WLACZONY = True  # False = ława zawsze analizuje SYMBOL
SCREENER_LICZBA_KANDYDATOW = 30  # najpłynniejsze pary USDT brane pod uwagę
SCREENER_MIN_WOLUMEN_USDT = 20_000_000  # wolumen 24h
SCREENER_MAKS_SPREAD_PROCENT = 0.05
SCREENER_MAKS_KOSZT_DO_ATR = 25.0  # koszt transakcji jako % ATR — analiza: 1h → mediana 23%
SCREENER_MIN_ATR_PROCENT = 0.15  # poniżej coin zachowuje się jak stablecoin
SCREENER_OKNO_ATR = 24  # mediana ATR% z ostatnich świec (przy 1h: doba)
SCREENER_SWIECE = 100  # pobierane na kandydata (rozgrzewka ATR + okno)
MAKS_OTWARTYCH_POZYCJI = 1  # łącznie, na wszystkich parach (crypto mocno skorelowane)
# Przeszukiwanie rynku: gdy ława powie NIE, analizuje kolejną parę z rankingu screenera
# (nigdy tej samej ponownie), aż do otwarcia pozycji albo wyczerpania limitu.
# Koszt LLM rośnie maks. tyle razy — przy 4: do ok. $0.016 zamiast $0.004 na świecę.
MAKS_PAR_NA_SWIECE = 4
# Brak w API Binance pola odróżniającego tokenizowane akcje/złoto — lista ręczna,
# uzupełniać, gdy w rankingu screenera pojawi się nowy taki token.
WYKLUCZONE_AKTYWA = {
    # stablecoiny i aktywa „opakowane”
    "USDC", "FDUSD", "TUSD", "DAI", "USDP", "BUSD", "USDE", "PYUSD", "USD1", "BFUSD", "XUSD",
    "EUR", "AEUR", "EURI", "USDS", "RLUSD", "WBTC", "WBETH", "U",
    # tokenizowane złoto, akcje i ETF-y
    "PAXG", "XAUT", "SNDKB", "SOXLB", "CRCLB", "SPCXB", "MUB", "MSTRB",
}

# --- Symulator ---
OPOZNIENIE_PO_ZAMKNIECIU_S = 20  # odczekanie po zamknięciu świecy, aż giełda ją opublikuje
PROBY_CYKLU = 3  # ile razy ponowić cykl po błędzie (sieć, API)
PRZERWA_PO_BLEDZIE_S = 60
# Logika wyjścia (minimalna): SL, TP albo zamknięcie po czasie — day trading, nie trzymamy dni.
MAKS_CZAS_POZYCJI_SWIEC = 24  # przy 1h: doba
INTERWAL_ROZSTRZYGANIA = "1m"  # gdy SL i TP w tej samej świecy — sprawdzamy świece 1m
REFERENCJA_SL_ATR = 1.0  # transakcja referencyjna: SL = 1 × ATR, TP = minimalny po kosztach

# --- Świece ---
# Wskaźniki wygładzane wykładniczo potrzebują "rozgrzewki" — im więcej świec,
# tym mniejszy wpływ wartości startowej (przy 300 świecach błąd jest pomijalny).
LIMIT_SWIEC = 300
MIN_SWIEC = 100
SWIECE_W_PROMPCIE = 25
SWIECE_KROTKIE_W_PROMPCIE = 8

# --- Wskaźniki ---
OKRES_RSI = 14
MACD_SZYBKI = 12
MACD_WOLNY = 26
MACD_SYGNAL = 9
OKRES_ATR = 14
OKRES_SREDNIEGO_WOLUMENU = 20
OKRES_TRENDU_WOLUMENU = 5
PROG_TRENDU_WOLUMENU = 5.0  # % zmiany na świecę (nachylenie prostej)

# --- Cennik modeli OpenAI: USD za 1M tokenów (wejście, wejście z cache, wyjście) ---
# Stan z developers.openai.com/api/docs/pricing na 2026-10-24 — aktualizować ręcznie.
CENNIK_MODELI = {
    "gpt-6.1-sol": (2.00, 0.10, 10.00),
    "gpt-6-luna": (0.10, 0.01, 0.50),
    "gpt-5.6-luna": (0.20, 0.02, 1.20),
    "gpt-5-mini": (0.25, 0.025, 2.00),
    "gpt-5-nano": (0.05, 0.005, 0.40),
    "gpt-4.1-mini": (0.40, 0.10, 1.60),
}

# --- Statystyki (blok danych statystyka) ---
OKNO_KROTKIE = 24  # przy 1h: doba
OKNO_DLUGIE = 168  # przy 1h: tydzień
OKNO_ZSCORE = 20
OKNO_ZAKRESU = 50
OKNO_AUTOKORELACJI = 100
