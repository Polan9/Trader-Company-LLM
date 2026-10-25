// Formatowanie liczb i dat w UI (napisy po angielsku, czas lokalny przeglądarki).

export const procent = (x: number | null | undefined, miejsca = 2) =>
  x === null || x === undefined ? "—" : `${x > 0 ? "+" : ""}${x.toFixed(miejsca)}%`;

export const liczbaR = (x: number | null | undefined) =>
  x === null || x === undefined ? "—" : `${x > 0 ? "+" : ""}${x.toFixed(2)} R`;

export const usd = (x: number | null | undefined, miejsca = 2) =>
  x === null || x === undefined ? "—" : `$${x.toFixed(miejsca)}`;

/** Cena z cyframi znaczącymi — tanie coiny mają ceny rzędu 0.0001. */
export const cena = (x: number | null | undefined) =>
  x === null || x === undefined ? "—" : Number(x.toPrecision(6)).toString();

export const czas = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString("en-GB", { dateStyle: "short", timeStyle: "short" }) : "—";

/** Świeca 1h trwa od czasu otwarcia przez godzinę — pokazujemy zakres. */
export const zakresSwiecy = (iso: string) => {
  const poczatek = new Date(iso);
  const koniec = new Date(poczatek.getTime() + 3_600_000);
  const godzina = (d: Date) => d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  return `${poczatek.toLocaleDateString("en-GB")} ${godzina(poczatek)}–${godzina(koniec)}`;
};
