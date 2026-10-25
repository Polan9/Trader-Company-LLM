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

/** Sterowanie odtwarzaniem: krok co `krokMs`, po ostatnim kroku zatrzymuje się. `indeks = null` — tryb „na żywo”. */
export function uzyjOdtwarzania(kroki: Krok[], krokMs = 1400) {
  const [indeks, ustawIndeks] = useState<number | null>(null);

  useEffect(() => {
    if (indeks === null) return;
    if (indeks >= kroki.length - 1) {
      const koniec = setTimeout(() => ustawIndeks(null), krokMs * 2);
      return () => clearTimeout(koniec);
    }
    const zegar = setTimeout(() => ustawIndeks(indeks + 1), krokMs);
    return () => clearTimeout(zegar);
  }, [indeks, kroki.length, krokMs]);

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
