import { useCallback, useEffect, useState } from "react";

/** Pobiera dane z API i odświeża je co `odswiezanieMs` (symulator dopisuje rundy co godzinę). */
export function uzyjDanych<T>(pobierz: () => Promise<T>, zaleznosci: unknown[] = [], odswiezanieMs = 60_000) {
  const [dane, ustawDane] = useState<T | null>(null);
  const [blad, ustawBlad] = useState<string | null>(null);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const zaladuj = useCallback(() => {
    pobierz()
      .then((wynik) => {
        ustawDane(wynik);
        ustawBlad(null);
      })
      .catch((e: Error) => ustawBlad(e.message));
  }, zaleznosci);

  useEffect(() => {
    zaladuj();
    const zegar = setInterval(zaladuj, odswiezanieMs);
    return () => clearInterval(zegar);
  }, [zaladuj, odswiezanieMs]);

  return { dane, blad, odswiez: zaladuj };
}
