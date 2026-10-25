"""Uruchomienie symulatora: python -m symulacja [--raz]"""
import argparse

from dotenv import load_dotenv

from konfiguracja.lawa import wczytaj_konfiguracje_lawy
from konfiguracja.ustawienia import BUDZET_POCZATKOWY, PLIK_BAZY, PLIK_ENV
from main import stan_poczatkowy, zbuduj_graf
from symulacja.petla import log, skonfiguruj_logi, uruchom
from zapis import baza


def main() -> None:
    parser = argparse.ArgumentParser(description="Symulator ławy traderów (paper trading).")
    parser.add_argument("--raz", action="store_true", help="wykonaj jeden cykl i zakończ")
    argumenty = parser.parse_args()

    load_dotenv(PLIK_ENV)
    skonfiguruj_logi()
    polaczenie = baza.polacz(PLIK_BAZY)
    baza.inicjalizuj(polaczenie, BUDZET_POCZATKOWY)
    log.info(f"Start symulatora — baza: {PLIK_BAZY}, budżet: {baza.aktualny_budzet(polaczenie):.2f} USD")

    try:
        uruchom(polaczenie, zbuduj_graf(wczytaj_konfiguracje_lawy()), stan_poczatkowy(), raz=argumenty.raz)
    except KeyboardInterrupt:
        log.info("Zatrzymano przez użytkownika.")
    finally:
        polaczenie.close()


if __name__ == "__main__":
    main()
