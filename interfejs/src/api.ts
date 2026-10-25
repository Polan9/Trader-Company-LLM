// Typy i zapytania do API (FastAPI: api/serwer.py). Wszystkie endpointy tylko do odczytu.

export interface Pozycja {
  id: number;
  symbol: string;
  czas_wejscia: string;
  cena_wejscia: number;
  stop_loss: number;
  take_profit: number;
  wielkosc_usd: number;
  ryzyko_usd: number;
  status: string;
  powod: string | null;
  wynik_usd: number | null;
  wynik_r: number | null;
}

export interface Stan {
  budzet_poczatkowy: number;
  budzet: number;
  wynik_procent: number;
  koszt_llm_usd: number;
  liczba_rund: number;
  ostatnia_swieca: string | null;
  ostatnia_iteracja_ms: number | null;
  ostatnia_iteracja_kompletna: boolean; // symulator skończył zapisywać rundy tej iteracji
  zamkniete_pozycje: number;
  wygrane_pozycje: number;
  otwarte_pozycje: Pozycja[];
}

export interface SkrotRundy {
  id: number;
  symbol: string;
  pominieta: boolean;
  decyzja: "TAK" | "NIE" | null;
  tak: number | null;
  nie: number | null;
  otworz_pozycje: boolean;
  powody: string[];
}

export interface Iteracja {
  id: number;
  czas_swiecy: string;
  koszt_llm_usd: number;
  rundy: SkrotRundy[];
}

export interface Opinia {
  trader_id: string;
  nazwa: string;
  model: string;
  glos: "TAK" | "NIE";
  uzasadnienie: string;
  stop_loss: number | null;
  take_profit: number | null;
  skala_pozycji: number | null;
  pewnosc: number | null; // 0–100 deklarowana przez tradera (null: starsze rundy / głos unieważniony)
  uwagi: string[];
}

export interface Ocena {
  id: number;
  kto: string;
  cena_wejscia: number;
  stop_loss: number;
  take_profit: number;
  status: "otwarta" | "zamknieta";
  powod: string | null;
  wynik_procent: number | null;
  wynik_r: number | null;
}

export interface ParaScreenera {
  symbol: string;
  koszt_do_atr: number;
  atr_procent: number;
  spread_procent: number;
  wolumen_usdt_24h: number;
}

export interface Runda {
  id: number;
  symbol: string;
  interwal: string;
  pominieta: boolean;
  cena_wejscia: number | null;
  atr: number | null;
  koszt_procent: number | null;
  decyzja: "TAK" | "NIE" | null;
  otworz_pozycje: boolean;
  powody: string[];
  koszt_llm_usd: number;
  glosowanie: { tak: number; nie: number; decyzja: string } | null;
  head_trader: { stop_loss: number; take_profit: number; uzasadnienie: string; zrodlo: string; uwagi: string[] } | null;
  decyzja_koncowa: Record<string, unknown> | null;
  ticker: Record<string, number | string | null> | null;
  analiza: {
    rsi: { wartosc: number; strefa: string };
    macd: { interpretacja: string };
    atr: { procent_ceny: number };
    wolumen: { zmiana_procent_vs_srednia: number; interpretacja: string };
    statystyki: { zscore_ceny: number; pozycja_w_zakresie: number; autokorelacja_lag1: number };
  } | null;
  opinie: Opinia[];
  oceny: Ocena[];
  pozycja: Pozycja | null;
}

export interface SzczegolyIteracji {
  id: number;
  czas_swiecy: string;
  koszt_llm_usd: number;
  screener: { symbol: string | null; ranking: ParaScreenera[]; odrzucone: { symbol: string; odrzucenia: string[] }[] } | null;
  rundy: Runda[];
}

export interface Swieca {
  czas: number;
  open: number;
  high: number;
  low: number;
  close: number;
}

export interface StatystykiTransakcji {
  liczba: number;
  skutecznosc_procent?: number;
  sredni_r?: number;
  suma_r?: number;
  profit_factor?: number | null;
}

export interface WierszKarty {
  trader: string;
  model: string; // karta liczona osobno dla każdego modelu tradera (porównanie przed/po zmianie)
  glosy: number;
  tak_procent: number;
  rozstrzygniete: number;
  trafnosc_procent: number | null;
  trafnosc_tak_procent: number | null;
  sredni_r_tak: number | null;
  srednia_pewnosc: number | null;
  trafnosc_nie_procent: number | null;
}

export interface WierszPewnosci {
  glos: "TAK" | "NIE";
  przedzial: string;
  liczba: number;
  trafnosc_procent: number | null;
  sredni_r: number | null;
}

export interface Statystyki {
  lawa: StatystykiTransakcji;
  zawsze_wchodz: StatystykiTransakcji;
  heurystyka: StatystykiTransakcji;
  maks_spadek_procent: number;
  krzywa_kapitalu: { czas: string | null; budzet: number }[];
  kup_i_trzymaj_btc: { zmiana_procent: number; netto_procent: number } | null;
  kup_i_trzymaj_pary: { symbol: string; netto_procent: number }[];
  karta_traderow: WierszKarty[];
  trafnosc_wg_pewnosci: WierszPewnosci[];
  koszt_llm_dziennie: { dzien: string; koszt_usd: number; rundy: number }[];
}

export interface Lawa {
  traderzy: { id: string; nazwa: string; aktywny: boolean; fokus: string; model: string }[];
  head_trader: { nazwa: string; model: string };
}

async function pobierz<T>(sciezka: string): Promise<T> {
  const odpowiedz = await fetch(sciezka);
  if (!odpowiedz.ok) {
    const tresc = await odpowiedz.text();
    throw new Error(`${odpowiedz.status}: ${tresc}`);
  }
  return odpowiedz.json() as Promise<T>;
}

export const api = {
  stan: () => pobierz<Stan>("/api/stan"),
  iteracje: (limit = 50) => pobierz<Iteracja[]>(`/api/iteracje?limit=${limit}`),
  iteracja: (id: number) => pobierz<SzczegolyIteracji>(`/api/iteracje/${id}`),
  swiece: (symbol: string, wokol: number) =>
    pobierz<Swieca[]>(`/api/swiece?symbol=${encodeURIComponent(symbol)}&wokol=${wokol}`),
  statystyki: () => pobierz<Statystyki>("/api/statystyki"),
  lawa: () => pobierz<Lawa>("/api/lawa"),
};
