# Uruchamia symulator w tle (Windows): bez okna konsoli, wyjście do plików w dane_lokalne\logi.
# Bez widocznego okna nie da się przypadkiem włączyć trybu zaznaczania (QuickEdit), który
# wstrzymuje program przy pierwszym wypisaniu na ekran.
# Użycie (z katalogu projektu): & .\narzedzia\uruchom_symulator.ps1
$projekt = Split-Path -Parent $PSScriptRoot
$logi = Join-Path $projekt 'dane_lokalne\logi'
New-Item -ItemType Directory -Force -Path $logi | Out-Null
Start-Process -FilePath (Join-Path $projekt '.venv\Scripts\python.exe') `
    -ArgumentList '-X', 'utf8', '-m', 'symulacja' `
    -WorkingDirectory $projekt -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logi 'symulator_wyjscie.log') `
    -RedirectStandardError (Join-Path $logi 'symulator_bledy.log')
Write-Output "Symulator uruchomiony w tle. Log: $logi\symulacja.log"
# Osobne okno z logami na bieżąco (tylko podgląd — nie wstrzymuje symulatora)
& (Join-Path $PSScriptRoot 'pokaz_logi.ps1')
