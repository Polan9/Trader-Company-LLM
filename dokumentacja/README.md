# Dokumentacja Trader Company

Opis każdej funkcji i klasy w projekcie: co robi i jak działa. Zasady projektu
(decyzje, konwencje) są w [`.claude/CLAUDE.md`](../.claude/CLAUDE.md) — tutaj jest opis kodu.

## Jak to działa w skrócie

Jedna **runda** to przejście grafu LangGraph:

```
pobierz_dane → analiza_techniczna → [traderzy równolegle] → glosowanie
                                                              ├─ NIE → koniec
                                                              └─ TAK → head_trader → risk_manager → koniec
```

1. **Dane** — ticker i świece z Binance (tylko zamknięte świece).
2. **Wskaźniki** — RSI, MACD, ATR, wolumen, statystyki (czysty Python, bez LLM).
3. **Ława** — każdy aktywny trader z `konfiguracja/lawa.json` dostaje dane swojej roli
   i głosuje TAK/NIE z SL/TP; głos łamiący reguły zamieniany jest na NIE.
4. **Głosowanie** — TAK > NIE; liczy medianę i zakres SL/TP z głosów TAK.
5. **Head Trader** — wybiera SL/TP z zakresu; błąd → mediana.
6. **Risk Manager** — weto (limity, reguły) i wielkość pozycji.

**Symulator** (`python -m symulacja`) powtarza rundę co godzinę, prowadzi wirtualny
portfel w SQLite i rozlicza transakcje na kolejnych świecach.

## Uruchamianie

| Polecenie | Co robi |
|---|---|
| `.venv\Scripts\python.exe main.py` | jedna runda, wynik w `trading_state.txt` |
| `.venv\Scripts\python.exe -m symulacja` | symulator — pętla co godzinę |
| `.venv\Scripts\python.exe -m symulacja --raz` | jeden cykl symulatora |
| `.venv\Scripts\python.exe -m symulacja.raport` | raport skuteczności z bazy |
| `.venv\Scripts\python.exe -m analizy.atr_vs_koszty` | analiza ATR vs koszty |

## Spis modułów

| Plik dokumentacji | Moduły |
|---|---|
| [main_i_stan.md](main_i_stan.md) | `main.py`, `stan.py` |
| [konfiguracja.md](konfiguracja.md) | `konfiguracja/ustawienia.py`, `konfiguracja/lawa.py`, `konfiguracja/lawa.json` |
| [dane.md](dane.md) | `dane/gielda.py` |
| [wskazniki.md](wskazniki.md) | `wskazniki/obliczenia.py`, `wskazniki/analiza_techniczna.py`, `wskazniki/statystyki.py` |
| [lawa.md](lawa.md) | `lawa/*` — traderzy, głosowanie, Head Trader, Risk Manager, reguły SL/TP, LLM |
| [symulacja.md](symulacja.md) | `symulacja/*` — pętla, ocena transakcji, raport |
| [zapis.md](zapis.md) | `zapis/baza.py`, `zapis/plik_stanu.py` |
| [analizy.md](analizy.md) | `analizy/atr_vs_koszty.py` |

## Pojęcia

- **R** — jednostka ryzyka: strata przy trafieniu SL **po kosztach**. Wynik +1.5 R = zysk
  1,5 raza większy od tego, co ryzykowaliśmy.
- **Koszt transakcji** — 2 × (prowizja + poślizg) + spread, w % wartości pozycji.
- **Transakcja referencyjna** — w każdej rundzie hipotetyczne wejście z SL = 1×ATR
  i minimalnym TP po kosztach; miara dla głosów NIE i strategia odniesienia.
- **Zamknięta świeca** — świeca, której czas się skończył; trwającą zawsze odrzucamy.
