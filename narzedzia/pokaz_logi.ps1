# Otwiera okno z logiem symulatora na bieżąco (podgląd ostatnich 40 linii + nowe wpisy).
# To tylko podgląd pliku — symulator działa osobno, więc kliknięcie w to okno (tryb zaznaczania)
# wstrzymuje najwyżej wyświetlanie, nigdy sam symulator. Zamknięcie okna nic nie zatrzymuje.
# Użycie (z katalogu projektu): & .\narzedzia\pokaz_logi.ps1
$projekt = Split-Path -Parent $PSScriptRoot
$log = Join-Path $projekt 'dane_lokalne\logi\symulacja.log'
$polecenie = "`$Host.UI.RawUI.WindowTitle = 'Trader Company - logi symulatora'; " +
    "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; " +
    "Get-Content -Path '$log' -Wait -Tail 40 -Encoding UTF8"
Start-Process powershell -ArgumentList '-NoExit', '-NoProfile', '-Command', $polecenie
