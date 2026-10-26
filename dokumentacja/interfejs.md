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
Typy danych zwracanych przez API (`Pozycja`, `Stan`, `SkrotRundy`, `Iteracja`, `Opinia`, `Ocena`,
`ParaScreenera`, `Runda`, `SzczegolyIteracji`, `Swieca`, `StatystykiTransakcji`, `WierszKarty`,
`Statystyki`, `Lawa`) i obiekt `api` z funkcjami zapytań (`stan`, `iteracje`, `iteracja`, `swiece`,
`statystyki`, `lawa`). `pobierz<T>(sciezka)` — wspólne `fetch`, błąd HTTP → wyjątek z treścią odpowiedzi.

### `src/uzyjDanych.ts`
**`uzyjDanych(pobierz, zaleznosci, odswiezanieMs=60000)`** — hook React: pobiera dane przy montowaniu
i co minutę (symulator dopisuje rundy co godzinę). Zwraca `{dane, blad, odswiez}`.

### `src/formaty.ts`
Formatowanie: `procent`, `liczbaR`, `usd`, `cena` (6 cyfr znaczących — tanie coiny), `czas`,
`zakresSwiecy` (zakres godzin świecy w czasie lokalnym przeglądarki).

### `src/App.tsx`
Nagłówek ze stanem portfela (budżet, otwarte pozycje, koszt LLM, ostatnia świeca) i trzy zakładki
(typ `Zakladka`, lista `ZAKLADKI`): Preview, Reports, Statistics. Domyślnie otwiera Reports.

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
**`WykresSwiec({symbol, wokolMs, poziomy})`** (`Poziom` = cena, kolor, etykieta linii) — wykres świec (lightweight-charts) od doby przed decyzją
do teraz; poziomy jako przerywane linie z etykietą, strzałka „decision” nad świecą decyzji.
Oś czasu wykresu jest w UTC.

### `src/zakladki/Statystyki.tsx` — Statistics
- **`Statystyki`** — kafelki: transakcje ławy, „zawsze wchodź”, heurystyka RSI/MACD, kup i trzymaj
  (BTC i analizowane pary), maks. spadek; karta traderów (osobno dla każdego modelu tradera,
  ze średnią pewnością); tabela
  **trafność wg deklarowanej pewności** (`WierszPewnosci`); koszt LLM dziennie. Wykresy — etap 3.
- **`Kafelek`** — liczba transakcji, skuteczność, średni i łączny R, profit factor.

### `src/zakladki/Podglad.tsx` — Preview (makieta biura 3D)
- **`Podglad`** — płótno 3D (`Canvas`), światła, sterowanie kamerą `CameraControls` (obrót, przybliżenie,
  przesunięcie — mysz i dotyk), przyciski widoków (`WIDOKI`: Overview, Trading room, Head Trader, Staff)
  z płynnym przejściem kamery, przycisk **Replay last iteration** / **Stop (krok/liczba)**.
  Kliknięcie w puste miejsce zamyka panel.
- **Auto-odtwarzanie (dynamiczne iteracje):** stan z API odpytywany co `ODSWIEZANIE_STANU_MS` (15 s).
  Gdy pojawi się **nowa, kompletna** iteracja (`ostatnia_iteracja_kompletna` z API), odtwarza się sama
  i kamera wraca do widoku ogólnego. Iteracja pobierana jest razem z flagą kompletności z chwili
  pobrania — żeby nie odtworzyć niepełnej iteracji, gdy symulator wciąż zapisuje kolejne pary.
  Przy pierwszym wejściu na stronę tylko zapamiętuje bieżącą iterację (bez odtwarzania).
  Przycisk **Auto-replay: on/off**; wybór zapamiętany w przeglądarce (`KLUCZ_AUTO`, `czytajAuto`,
  `przelaczAuto` — bez pamięci przeglądarki działa do odświeżenia strony). Działa tylko, gdy
  zakładka Preview jest otwarta.
- **`PanelWyboru`** — panel po kliknięciu osoby: trader (głosy w ostatniej iteracji z SL/TP, wynikiem
  oceny, uzasadnieniem i uwagami), Head Trader (wybrane SL/TP albo „nie wołany”), Screener (ranking),
  Risk Manager (zatwierdzenie / weto), Execution i Researcher (status modułów).

## `src/biuro/` — komponenty makiety

### `uklad.ts` — wymiary i pozycje
- `SALA` (główny pokój 16×16, środek w (0,0)), `POKOJ` (pokoje po prawej 8×8), `X_POKOI`,
  `SRODEK_HEAD_TRADERA`, `SRODEK_PERSONELU`, `SRODEK_BIURA`, `WYSOKOSC_SCIANY`, `WYSOKOSC_SCIANKI`,
  `GRUBOSC_SCIANY`, `SZEROKOSC_DRZWI`, `STOL` (półosie i wysokość stołu), `MIEJSCA` (elipsa krzeseł),
  `STANOWISKO_HEAD_TRADERA`, `PERSONEL` (typ `RolaPersonelu`; rola, nazwa, pozycja, kolor: Screener,
  Risk Manager, Researcher, Execution), `WIDOKI` (pozycje kamery), `KOLORY`, typ `V3` (punkt [x, y, z]).
- **`miejscePrzyStole(indeks, liczba)`** — pozycja na elipsie wokół stołu i obrót twarzą do środka
  (`atan2(-x, -z)`); pierwsze miejsce od strony widza.

### `Sciany.tsx`
- `DefinicjaSciany` — środek, długość, kierunek, normalna (null = ściana wewnętrzna), wysokość.
- **`zDrzwiami(od, do, drzwi)`** — dzieli ścianę na odcinki z przerwami na drzwi.
- **`scianyBiura()`** — wszystkie ściany: zewnętrzne trzech pokoi, ściana sala↔pokoje po prawej z dwojgiem
  drzwi, niska ścianka między gabinetem Head Tradera a personelem z przejściem.
- **`ScianaZanikajaca`** — co klatkę sprawdza, czy kamera jest po zewnętrznej stronie ściany
  (iloczyn skalarny z normalną); jeśli tak — płynnie robi ją prawie przezroczystą. Dzięki temu przy
  każdym obrocie widać wnętrze, jak w makiecie bez frontowych ścian.
- **`Sciany`** — renderuje wszystkie ściany.

### `Meble.tsx`
- **`Podlogi`** — podstawa makiety, podłogi trzech pokoi (różne kolory), owalny dywan pod stołem.
- **`StolOwalny({swiatlo})`** — blat i dwie nogi; `swiatlo` = kolor pulsującej poświaty (wynik głosowania).
- **`Krzeslo`**, **`Roslina`** — dekoracje.
- **`Biurko({pozycja, obrot, ekran, aktywne})`** — biurko z monitorem po stronie +Z; ekran świeci
  kolorem roli, gdy stanowisko jest aktywne w odtwarzaniu.

### `Postac.tsx`
**`Postac`** (właściwości: `WlasciwosciPostaci`) — postać z brył (tułów, głowa z oczami, ręce, przy staniu nogi), siedząca przy stole/biurku.
Pierścień pod postacią = kolor głosu (zielony TAK, czerwony NIE, szary brak). „Oddycha” (lekkie
falowanie), a **aktywna** (mówi w odtwarzaniu) podskakuje, a jej pierścień pulsuje. Tabliczka z nazwą
zawsze zwrócona do kamery; **dymek** (`Html` z drei) nad głową; podświetlenie i kursor po najechaniu.

### `Biuro.tsx`
- **`Biuro`** — cała scena dla bieżącego kroku: podłogi, ściany, stół, tablica, rośliny, traderzy przy
  stole (z `lawa.json`; nieaktywni przygaszeni), gabinet Head Tradera, pokój personelu, przepływy danych.
  Tryb „na żywo”: dymki pokazują głosy z ostatniej iteracji (np. „WLD NO ZEC YES”). Tryb odtwarzania:
  widać tylko głosy oddane do tej pory w bieżącej parze, mówiący trader ma w dymku początek uzasadnienia.
- **`dymekHeadTradera`**, **`dymekPersonelu`** — treść dymków (ranking i wybrana para screenera,
  SL/TP Head Tradera, zatwierdzenie/weto Risk Managera, status Execution i Researchera).
- Typ **`Wybor`** — kogo kliknięto (trader / Head Trader / rola personelu); `Wlasciwosci` — dane sceny.
- `KOSZULE_TRADEROW` — kolory koszul kolejnych traderów; `bezUsdt` — skraca „WLD/USDT” do „WLD”.

### `odtwarzanie.ts`
- Typ **`Krok`**: `screener` → dla każdej pary `para`, `glos` (każdy trader), `wynik`, przy TAK
  `head_trader` i `risk_manager` → `koniec`. Kolejność jak w `symulacja/petla.py`.
- **`zbudujKroki(iteracja)`** — lista kroków z danych iteracji.
- **`CZAS_KROKU_MS`** — czas trwania każdego rodzaju kroku: głos tradera i Head Trader 6 s
  (w dymku jest uzasadnienie do przeczytania, do 260 znaków), Risk Manager 4,5 s, screener i wynik 3,5 s,
  ogłoszenie pary i koniec 3 s. Pełna iteracja z 4 parami trwa ok. 2 minuty.
- **`uzyjOdtwarzania(kroki)`** — hook: `graj`, `zatrzymaj`, bieżący `krok` / `indeks`;
  każdy krok trwa `CZAS_KROKU_MS[typ]`, po ostatnim wraca do trybu na żywo.
- **`aktywnyAktor(krok)`** — kto „mówi” (id tradera, `screener`, `head_trader`, `risk_manager`).
- **`glosyDoTejPory(kroki, indeks)`** — głosy oddane do bieżącego kroku w bieżącej parze.

### `Przeplyw.tsx`
**`Przeplyw({od, do, kolor})`** — przerywany łuk nad makietą i świecąca kulka biegnąca po nim:
screener → stół (ogłoszenie pary), stół → Head Trader, Head Trader → Risk Manager.

### `Tablica.tsx`
**`Tablica({stan, iteracja, krok})`** — ekran na północnej ścianie sali: budżet, otwarte pozycje,
czas iteracji i wyniki par; w odtwarzaniu — „Now discussing: PARA” i wynik głosowania.

### `src/style.css`
Ciemny motyw (zmienne CSS), układ zakładek, responsywność (≤ 800 px: jedna kolumna, tabele przewijane
w kartach — strona nie przewija się w poziomie).
