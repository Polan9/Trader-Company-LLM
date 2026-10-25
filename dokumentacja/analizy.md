# `analizy/` — jednorazowe analizy

## `analizy/atr_vs_koszty.py`

Uruchomienie: `python -m analizy.atr_vs_koszty`. Sprawdza, czy zmienność (ATR) na danym
interwale pokrywa koszty transakcji. Wynik zapisuje do `analizy/atr_vs_koszty_wynik.csv`
(ignorowany przez git). Na tej analizie oparty jest wybór interwału 1h.

Stałe na górze pliku: liczba coinów (30), interwały (5m, 15m, 1h, 4h), prowizje
(0.1% / 0.075% z BNB), SL = 1×ATR, TP = 1.5×ATR, lista wykluczonych stablecoinów.

### `_najplynniejsze_pary(gielda, liczba) -> DataFrame`
Aktywne pary spot `*/USDT` bez stablecoinów, posortowane po wolumenie 24h w USDT;
dla każdej spread % z tickera.

### `_mediana_atr_procent(gielda, symbol, interwal) -> float`
1000 świec (bez trwającej), ATR jako % ceny, mediana po pominięciu 50 pierwszych wartości (rozgrzewka).

### `_wymagana_skutecznosc(atr_procent, koszt_procent) -> float`
Skuteczność potrzebna do wyjścia na zero przy SL = 1×ATR i TP = 1.5×ATR z kosztami:
`p = (SL + k) / (TP + SL)`, gdzie `k` = koszt wyrażony w ATR. Bez kosztów: 40%.

### `main()`
Pobiera pary i ATR dla każdego interwału, liczy koszty i wymaganą skuteczność, drukuje
tabelę oraz podsumowanie (mediany po coinach), zapisuje CSV.

> Uwaga: ta analiza nie uwzględnia poślizgu i przyjmuje uproszczone SL/TP;
> reguła zysk/ryzyko w ławie jest liczona dokładniej (po kosztach, `lawa/sl_tp.py`).
