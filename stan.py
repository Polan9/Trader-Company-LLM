from typing import Any, Dict, TypedDict

import pandas as pd


class AktualnyStan(TypedDict):
    symbol: str
    interwal: str
    aktualne_dane: Dict[str, Any]
    dane_historyczne: pd.DataFrame
    analiza_techniczna: Dict[str, Any]
    decyzja_analityka: str
    decyzja_head_tradera: str
    budzet: float
