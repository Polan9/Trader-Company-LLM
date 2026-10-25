"""Uruchomienie serwera interfejsu: python -m api"""
import uvicorn

from konfiguracja.ustawienia import API_HOST, API_PORT

if __name__ == "__main__":
    uvicorn.run("api.serwer:aplikacja", host=API_HOST, port=API_PORT)
