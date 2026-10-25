// Układ makiety biura (jednostki sceny ≈ metry). Oś X: w prawo, oś Z: do widza, Y: w górę.

export type V3 = [number, number, number];

export const SALA = 16; // główny pokój: kwadrat SALA × SALA, środek w (0, 0)
export const POKOJ = 8; // dwa pokoje po prawej: każdy POKOJ × POKOJ
export const X_POKOI = SALA / 2 + POKOJ / 2; // środek pokoi po prawej w osi X
export const SRODEK_HEAD_TRADERA: V3 = [X_POKOI, 0, -POKOJ / 2];
export const SRODEK_PERSONELU: V3 = [X_POKOI, 0, POKOJ / 2];
export const SRODEK_BIURA: V3 = [POKOJ / 2, 0, 0]; // środek całej makiety (do obrotu kamery)

export const WYSOKOSC_SCIANY = 2.4;
export const WYSOKOSC_SCIANKI = 1.1; // niska ścianka działowa między pokojami po prawej
export const GRUBOSC_SCIANY = 0.2;
export const SZEROKOSC_DRZWI = 2;

export const STOL = { polosX: 4.2, polosZ: 2.4, wysokosc: 0.78 };
export const MIEJSCA = { polosX: 5.3, polosZ: 3.5 }; // elipsa krzeseł wokół stołu

export const STANOWISKO_HEAD_TRADERA: V3 = [X_POKOI, 0, -POKOJ / 2 - 1.2];

export type RolaPersonelu = "screener" | "risk_manager" | "researcher" | "execution";

export const PERSONEL: { rola: RolaPersonelu; nazwa: string; pozycja: V3; kolor: string }[] = [
  { rola: "screener", nazwa: "Screener", pozycja: [X_POKOI - 2, 0, 2.2], kolor: "#5fa8e8" },
  { rola: "risk_manager", nazwa: "Risk Manager", pozycja: [X_POKOI + 2, 0, 2.2], kolor: "#e87a5f" },
  { rola: "researcher", nazwa: "Researcher", pozycja: [X_POKOI - 2, 0, 5.8], kolor: "#a98be8" },
  { rola: "execution", nazwa: "Execution", pozycja: [X_POKOI + 2, 0, 5.8], kolor: "#7fc98a" },
];

/** Pozycja miejsca przy stole i obrót postaci twarzą do środka stołu. */
export function miejscePrzyStole(indeks: number, liczba: number): { pozycja: V3; obrot: number } {
  const kat = (indeks / liczba) * Math.PI * 2 + Math.PI / 2; // pierwsze miejsce od strony widza
  const x = Math.cos(kat) * MIEJSCA.polosX;
  const z = Math.sin(kat) * MIEJSCA.polosZ;
  return { pozycja: [x, 0, z], obrot: Math.atan2(-x, -z) };
}

/** Ustawienia kamery: skąd patrzy i na co (przyciski widoków). */
export const WIDOKI: Record<string, { etykieta: string; pozycja: V3; cel: V3 }> = {
  ogolny: { etykieta: "Overview", pozycja: [24, 22, 26], cel: SRODEK_BIURA },
  sala: { etykieta: "Trading room", pozycja: [0, 12, 14], cel: [0, 0.8, 0] },
  head_trader: { etykieta: "Head Trader", pozycja: [X_POKOI - 1, 7, 5], cel: SRODEK_HEAD_TRADERA },
  personel: { etykieta: "Staff", pozycja: [X_POKOI - 1, 8, 14], cel: SRODEK_PERSONELU },
};

export const KOLORY = {
  tak: "#26a69a",
  nie: "#ef5350",
  brak: "#8b97ab",
  nieaktywny: "#4a5568",
  akcent: "#f5c542",
  podlogaSali: "#6b5440",
  podlogaHeadTradera: "#46597d",
  podlogaPersonelu: "#4c5c66",
  sciana: "#d9dde3",
  podstawa: "#1a2333",
};
