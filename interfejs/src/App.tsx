import { useState } from "react";
import { api } from "./api";
import { procent, usd, zakresSwiecy } from "./formaty";
import { uzyjDanych } from "./uzyjDanych";
import Podglad from "./zakladki/Podglad";
import Raporty from "./zakladki/Raporty";
import Statystyki from "./zakladki/Statystyki";

type Zakladka = "podglad" | "raporty" | "statystyki";

const ZAKLADKI: { id: Zakladka; etykieta: string }[] = [
  { id: "podglad", etykieta: "Preview" },
  { id: "raporty", etykieta: "Reports" },
  { id: "statystyki", etykieta: "Statistics" },
];

export default function App() {
  const [zakladka, ustawZakladke] = useState<Zakladka>("raporty");
  const { dane: stan, blad } = uzyjDanych(api.stan);

  return (
    <div className="aplikacja">
      <header className="naglowek">
        <div className="logo">Trader Company</div>
        <nav className="zakladki">
          {ZAKLADKI.map((z) => (
            <button
              key={z.id}
              className={zakladka === z.id ? "zakladka aktywna" : "zakladka"}
              onClick={() => ustawZakladke(z.id)}
            >
              {z.etykieta}
            </button>
          ))}
        </nav>
        <div className="stan">
          {blad && <span className="blad">API: {blad}</span>}
          {stan && (
            <>
              <span>
                Budget <b>{usd(stan.budzet)}</b> <span className={stan.wynik_procent >= 0 ? "plus" : "minus"}>({procent(stan.wynik_procent)})</span>
              </span>
              <span>Open positions <b>{stan.otwarte_pozycje.length}</b></span>
              <span>LLM cost <b>{usd(stan.koszt_llm_usd, 3)}</b></span>
              {stan.ostatnia_swieca && <span className="przygaszony">Last candle {zakresSwiecy(stan.ostatnia_swieca)}</span>}
            </>
          )}
        </div>
      </header>
      <main className="tresc">
        {zakladka === "podglad" && <Podglad />}
        {zakladka === "raporty" && <Raporty />}
        {zakladka === "statystyki" && <Statystyki />}
      </main>
    </div>
  );
}
