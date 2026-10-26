import { useEffect, useState } from "react";
import { Opinia, Runda, SzczegolyIteracji } from "../api";

/** Jeden krok odtwarzania iteracji — kolejność taka, jak w kodzie symulatora (symulacja/petla.py). */
export type Krok =
  | { typ: "screener" }
  | { typ: "para"; runda: Runda }
  | { typ: "glos"; runda: Runda; opinia: Opinia }
  | { typ: "wynik"; runda: Runda }
  | { typ: "head_trader"; runda: Runda }
  | { typ: "risk_manager"; runda: Runda }
  | { typ: "koniec" };

/** Kroki iteracji: screener → dla każdej pary: ogłoszenie, głosy po kolei, wynik → (przy TAK) Head Trader, Risk Manager. */
export function zbudujKroki(iteracja: SzczegolyIteracji): Krok[] {
  const kroki: Krok[] = [];
  if (iteracja.screener) kroki.push({ typ: "screener" });
  for (const runda of iteracja.rundy.filter((r) => !r.pominieta)) {
    kroki.push({ typ: "para", runda });
    for (const opinia of runda.opinie) kroki.push({ typ: "glos", runda, opinia });
    kroki.push({ typ: "wynik", runda });
    if (runda.decyzja === "TAK") {
      kroki.push({ typ: "head_trader", runda });
      kroki.push({ typ: "risk_manager", runda });
    }
  }
  kroki.push({ typ: "koniec" });
  return kroki;
}

/** Ile trwa każdy rodzaj kroku (ms) — głos tradera najdłużej, bo w dymku jest uzasadnienie do przeczytania. */
export const CZAS_KROKU_MS: Record<Krok["typ"], number> = {
  screener: 3500,
  para: 3000,
  glos: 6000,
  wynik: 3500,
  head_trader: 6000,
  risk_manager: 4500,
  koniec: 3000,
};

/** Sterowanie odtwarzaniem: każdy krok trwa `CZAS_KROKU_MS[typ]`, po ostatnim wraca do trybu „na żywo” (`indeks = null`). */
export function uzyjOdtwarzania(kroki: Krok[]) {
  const [indeks, ustawIndeks] = useState<number | null>(null);

  useEffect(() => {
    if (indeks === null) return;
    const czas = CZAS_KROKU_MS[kroki[indeks].typ];
    const nastepny = indeks >= kroki.length - 1 ? null : indeks + 1;
    const zegar = setTimeout(() => ustawIndeks(nastepny), czas);
    return () => clearTimeout(zegar);
  }, [indeks, kroki]);

  return {
    krok: indeks === null ? null : kroki[indeks],
    indeks,
    liczbaKrokow: kroki.length,
    graj: () => ustawIndeks(0),
    zatrzymaj: () => ustawIndeks(null),
  };
}

/** Kto „mówi” w danym kroku (id tradera albo rola) — ta postać podskakuje i świeci. */
export function aktywnyAktor(krok: Krok | null): string | null {
  if (!krok) return null;
  switch (krok.typ) {
    case "screener":
    case "para":
      return "screener";
    case "glos":
      return krok.opinia.trader_id;
    case "head_trader":
      return "head_trader";
    case "risk_manager":
      return "risk_manager";
    default:
      return null;
  }
}

/** Głosy oddane do tej pory w bieżącej parze (w trakcie odtwarzania widać tylko je). */
export function glosyDoTejPory(kroki: Krok[], indeks: number | null): Map<string, Opinia> {
  const glosy = new Map<string, Opinia>();
  if (indeks === null) return glosy;
  const krok = kroki[indeks];
  const runda = "runda" in krok ? krok.runda : null;
  for (let i = 0; i <= indeks; i++) {
    const k = kroki[i];
    if (k.typ === "glos" && runda && k.runda.id === runda.id) glosy.set(k.opinia.trader_id, k.opinia);
  }
  return glosy;
}
