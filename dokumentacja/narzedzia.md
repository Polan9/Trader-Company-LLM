# `narzedzia/` — uruchamianie na Windows

Skrypty PowerShell do uruchamiania procesów na komputerze z Windows (do czasu wdrożenia na Raspberry Pi,
gdzie zastąpią je usługi systemd). Uruchamianie z katalogu projektu, np.:
`powershell -NoProfile -ExecutionPolicy Bypass -File .\narzedzia\uruchom_symulator.ps1`

## Dlaczego bez okna konsoli
Kliknięcie w okno konsoli Windows włącza **tryb zaznaczania** (QuickEdit — tytuł okna zaczyna się od
„Wybierz”). W tym trybie program jest **wstrzymywany przy pierwszej próbie wypisania czegoś na ekran**
i stoi, dopóki nie naciśnie się Esc. 2026-10-26 o 02:00 symulator zawisł w ten sposób w połowie rundy,
bez żadnego błędu w logu. Dlatego procesy działają bez okna, a ich wyjście trafia do plików.

## `uruchom_symulator.ps1`
Startuje `python -m symulacja` w tle (`-WindowStyle Hidden`); wyjście standardowe do
`dane_lokalne\logi\symulator_wyjscie.log`, błędy i logi konsolowe do `symulator_bledy.log`
(pełny log zdarzeń jest i tak w `symulacja.log`). Na koniec otwiera okno logów (`pokaz_logi.ps1`).

## `uruchom_interfejs.ps1`
Startuje `python -m api` w tle; wyjście do `interfejs_wyjscie.log` i `interfejs_bledy.log`.
Interfejs: http://127.0.0.1:8000.

## `pokaz_logi.ps1`
Otwiera osobne okno PowerShell z tytułem „Trader Company - logi symulatora”, które pokazuje 40 ostatnich
linii `symulacja.log` i dopisuje nowe na bieżąco (`Get-Content -Wait`). To **tylko podgląd pliku**:
kliknięcie w nie (tryb zaznaczania) wstrzymuje wyłącznie wyświetlanie, a zamknięcie okna niczego nie
zatrzymuje. Po kliknięciu wystarczy Esc, żeby podgląd ruszył dalej.

## Zatrzymywanie
Procesy uruchomione z karty terminala w aplikacji Claude kończą się po zamknięciu tej karty.
Uruchomione z własnego okna PowerShell — przez Menedżer zadań (python.exe) albo zamknięcie sesji.
Zatrzymywać **między rundami** (rundy startują o pełnej godzinie + ok. 20 s).
