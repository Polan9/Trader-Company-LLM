# `main.py` i `stan.py`

## `main.py` — składanie grafu i jedna runda

### `zbuduj_graf(konfiguracja: KonfiguracjaLawy)`
**Co robi:** buduje i kompiluje graf LangGraph jednej rundy.
**Jak działa:**
- dodaje węzły `pobierz_dane`, `analiza_techniczna`, `glosowanie`, `head_trader`, `risk_manager`,
- dla każdego **aktywnego** tradera z konfiguracji tworzy węzeł `trader_<id>` (fabryka
  `zbuduj_wezel_tradera`) i krawędź `analiza_techniczna → trader_<id>` — to daje równoległość (fan-out),
- `graf.add_edge([traderzy...], "glosowanie")` — głosowanie czeka na komplet opinii,
- krawędź warunkowa po głosowaniu (`po_glosowaniu`): TAK → `head_trader`, NIE → koniec.

**Zwraca:** skompilowany graf (`.invoke(stan)` uruchamia rundę).

### `stan_poczatkowy() -> AktualnyStan`
**Co robi:** zwraca pusty stan startowy rundy.
**Jak działa:** symbol, interwał i budżet z `konfiguracja/ustawienia.py`, puste słowniki
na dane/opinie/decyzje, liczniki dzienne = 0. Symulator nadpisuje budżet i liczniki wartościami z bazy.

### Blok `if __name__ == "__main__"`
Ładuje `.env`; gdy `SCREENER_WLACZONY` — uruchamia screener, wypisuje ranking i ustawia
wybraną parę (brak pary → koniec bez zwoływania ławy). Potem buduje graf, wykonuje **jedną**
rundę, wypisuje koszt LLM i zapisuje wynik do `trading_state.txt`. Nie używa bazy — do ręcznego sprawdzania.

## `stan.py`

### `class AktualnyStan(TypedDict)`
**Co to jest:** wspólny stan grafu — każdy węzeł czyta z niego i zwraca tylko zmienione pola.

| Pole | Kto wypełnia | Zawartość |
|---|---|---|
| `symbol`, `interwal`, `budzet` | start | para, interwał, aktualny budżet |
| `aktualne_dane` | `pobierz_dane` | ticker 24h + spread |
| `dane_historyczne` | `pobierz_dane` | DataFrame zamkniętych świec |
| `analiza_techniczna` | `oblicz_analize_techniczna` | wskaźniki, sygnały, statystyki |
| `opinie` | traderzy | `{id_tradera: opinia}` — **reducer `operator.or_`** scala słowniki z równoległych węzłów |
| `wynik_glosowania` | `glosowanie` | liczby głosów, decyzja, mediana/zakres SL/TP |
| `decyzja_head_tradera` | `head_trader` | wybrane SL/TP i źródło (head_trader / mediana) |
| `decyzja_koncowa` | `glosowanie` / `risk_manager` | otworzyć czy nie, powody, wielkość pozycji |
| `dzienna_strata_procent`, `transakcje_dzisiaj` | start (z bazy) | liczniki dla Risk Managera |
