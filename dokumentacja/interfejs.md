# `interfejs/` — aplikacja w przeglądarce (React + TypeScript + Vite)

Napisy w UI po angielsku, kod (identyfikatory) po polsku. Dane z backendu (uzasadnienia
traderów, interpretacje wskaźników) zostają po polsku — tak je generuje system.

## Budowanie i uruchamianie

| Polecenie (w `interfejs/`) | Co robi |
|---|---|
| `npm install` | instaluje zależności (wersje przypięte w `package.json`) |
| `npm run build` | sprawdza typy (`tsc`) i buduje do `interfejs/dist` — to serwuje `python -m api` |
| `npm run dev` | serwer deweloperski z podglądem zmian na żywo (http://localhost:5173), `/api` przekierowane do `python -m api` |

Na Raspberry Pi Node.js nie jest potrzebny — wystarczy skopiować zbudowany `dist/`.

## Pliki

### `src/api.ts`
Typy danych zwracanych przez API (`Stan`, `Iteracja`, `SzczegolyIteracji`, `Runda`, `Opinia`, `Ocena`,
`Statystyki`, `Lawa`, …) i obiekt `api` z funkcjami zapytań (`stan`, `iteracje`, `iteracja`, `swiece`,
`statystyki`, `lawa`). `pobierz<T>(sciezka)` — wspólne `fetch`, błąd HTTP → wyjątek z treścią odpowiedzi.

### `src/uzyjDanych.ts`
**`uzyjDanych(pobierz, zaleznosci, odswiezanieMs=60000)`** — hook React: pobiera dane przy montowaniu
i co minutę (symulator dopisuje rundy co godzinę). Zwraca `{dane, blad, odswiez}`.

### `src/formaty.ts`
Formatowanie: `procent`, `liczbaR`, `usd`, `cena` (6 cyfr znaczących — tanie coiny), `czas`,
`zakresSwiecy` (zakres godzin świecy w czasie lokalnym przeglądarki).

### `src/App.tsx`
Nagłówek ze stanem portfela (budżet, otwarte pozycje, koszt LLM, ostatnia świeca) i trzy zakładki
(lista `ZAKLADKI`): Preview, Reports, Statistics. Domyślnie otwiera Reports.

### `src/zakladki/Raporty.tsx` — Reports
- **`Raporty`** — lista iteracji po lewej (na telefonie nad podglądem), podgląd wybranej po prawej;
  domyślnie najnowsza.
- **`PozycjaListy`** — jedna iteracja na liście: zakres świecy, pary z wynikiem głosowania (TAK:NIE),
  koszt LLM, znaczniki OPENED / SKIPPED.
- **`PodgladIteracji`** — ranking screenera, przełącznik par z przeszukiwania, podgląd wybranej pary.
- **`PodgladRundy`** — wykres świec z ceną wejścia i SL/TP referencji, wskaźniki, karty opinii
  traderów (głos, SL/TP, wynik oceny, uzasadnienie, uwagi), Head Trader i Risk Manager (gdy byli
  wołani), tabela ocen (transakcji hipotetycznych) z wynikami.

### `src/komponenty/WykresSwiec.tsx`
**`WykresSwiec({symbol, wokolMs, poziomy})`** — wykres świec (lightweight-charts) od doby przed decyzją
do teraz; poziomy jako przerywane linie z etykietą, strzałka „decision” nad świecą decyzji.
Oś czasu wykresu jest w UTC.

### `src/zakladki/Statystyki.tsx` — Statistics
- **`Statystyki`** — kafelki: transakcje ławy, „zawsze wchodź”, heurystyka RSI/MACD, kup i trzymaj
  (BTC i analizowane pary), maks. spadek; karta traderów; koszt LLM dziennie. Wykresy — etap 3.
- **`Kafelek`** — liczba transakcji, skuteczność, średni i łączny R, profit factor.

### `src/zakladki/Podglad.tsx` — Preview (makieta biura 3D)
Etap 1: układ pokoi i ostatnie głosy. Obracanie / przybliżanie / przesuwanie: `OrbitControls` (mysz i dotyk).
- Stałe układu: `SALA` (główny pokój 16×16), `POKOJ` (pokoje po prawej 8×8), `WYSOKOSC_SCIANY`,
  `STOL` (półosie owalnego stołu), `MIEJSCA` (półosie elipsy krzeseł), `KOLOR`.
- **`Podglad`** — scena: główny pokój ze stołem i miejscami dla wszystkich traderów z `lawa.json`,
  po prawej gabinet Head Tradera i pokój pozostałych (Risk Manager, Screener, Researcher, Execution).
  Kliknięcie tradera → panel z jego głosami i uzasadnieniami z ostatniej iteracji.
- **`Pokoj`** — podłoga, cztery niskie półprzezroczyste ściany, podpis na podłodze.
- **`StolOwalny`** — blat (spłaszczony walec) i noga.
- **`MiejsceTradera`** — krzesło i postać na elipsie wokół stołu; kolor: zielony = choć jedno TAK
  w ostatniej iteracji, czerwony = same NIE, szary = brak głosów / nieaktywny.
- **`Postac`** — postać (kapsuła) z tabliczką zawsze zwróconą do kamery; podświetlenie po najechaniu.

### `src/style.css`
Ciemny motyw (zmienne CSS), układ zakładek, responsywność (≤ 800 px: jedna kolumna, tabele przewijane
w kartach — strona nie przewija się w poziomie).
