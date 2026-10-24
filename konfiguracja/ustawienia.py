from pathlib import Path

# --- Ścieżki ---
KATALOG_PROJEKTU = Path(__file__).resolve().parent.parent
PLIK_ENV = KATALOG_PROJEKTU / ".env"
PLIK_STANU = KATALOG_PROJEKTU / "trading_state.txt"

# --- Rynek ---
SYMBOL = "BTC/USDT"
INTERWAL = "15m"
BUDZET_POCZATKOWY = 1000.0

# --- Świece ---
# Wskaźniki wygładzane wykładniczo potrzebują "rozgrzewki" — im więcej świec,
# tym mniejszy wpływ wartości startowej (przy 300 świecach błąd jest pomijalny).
LIMIT_SWIEC = 300
MIN_SWIEC = 100
SWIECE_W_PROMPCIE = 25

# --- Wskaźniki ---
OKRES_RSI = 14
MACD_SZYBKI = 12
MACD_WOLNY = 26
MACD_SYGNAL = 9
OKRES_ATR = 14
OKRES_SREDNIEGO_WOLUMENU = 20
OKRES_TRENDU_WOLUMENU = 5
PROG_TRENDU_WOLUMENU = 5.0  # % zmiany na świecę (nachylenie prostej)

# --- LLM ---
MODEL_ANALITYKA = "gpt-4o-mini"
