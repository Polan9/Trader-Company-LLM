# Uruchamia serwer interfejsu w tle (Windows): bez okna konsoli, wyjście do plików w dane_lokalne\logi.
# Powód jak w uruchom_symulator.ps1 — kliknięte okno konsoli (QuickEdit) wstrzymuje proces.
# Użycie (z katalogu projektu): & .\narzedzia\uruchom_interfejs.ps1   → http://127.0.0.1:8000
$projekt = Split-Path -Parent $PSScriptRoot
$logi = Join-Path $projekt 'dane_lokalne\logi'
New-Item -ItemType Directory -Force -Path $logi | Out-Null
Start-Process -FilePath (Join-Path $projekt '.venv\Scripts\python.exe') `
    -ArgumentList '-X', 'utf8', '-m', 'api' `
    -WorkingDirectory $projekt -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logi 'interfejs_wyjscie.log') `
    -RedirectStandardError (Join-Path $logi 'interfejs_bledy.log')
Write-Output "Interfejs uruchomiony w tle: http://127.0.0.1:8000"
