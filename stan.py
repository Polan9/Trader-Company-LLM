import operator
from typing import Annotated, Any, Dict, TypedDict

import pandas as pd


class AktualnyStan(TypedDict):
    symbol: str
    interwal: str
    budzet: float
    aktualne_dane: Dict[str, Any]
    dane_historyczne: pd.DataFrame
    analiza_techniczna: Dict[str, Any]
    # Traderzy działają równolegle — każdy dopisuje swoją opinię pod własnym id
    opinie: Annotated[Dict[str, Dict[str, Any]], operator.or_]
    wynik_glosowania: Dict[str, Any]
    decyzja_head_tradera: Dict[str, Any]
    decyzja_koncowa: Dict[str, Any]
    # Liczniki dzienne dla Risk Managera — do czasu bazy danych podawane z zewnątrz
    dzienna_strata_procent: float
    transakcje_dzisiaj: int
