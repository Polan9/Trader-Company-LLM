import { Html } from "@react-three/drei";
import { Stan, SzczegolyIteracji } from "../api";
import { procent, usd, zakresSwiecy } from "../formaty";
import { Krok } from "./odtwarzanie";
import { SALA } from "./uklad";

/** Tablica na północnej ścianie sali: portfel i ostatnia iteracja (w trakcie odtwarzania — bieżąca para). */
export default function Tablica({ stan, iteracja, krok }: { stan: Stan | null; iteracja: SzczegolyIteracji | null; krok: Krok | null }) {
  const runda = krok && "runda" in krok ? krok.runda : null;
  return (
    <group position={[0, 0, -SALA / 2 + 0.15]}>
      <mesh position={[0, 1.9, 0]}>
        <boxGeometry args={[6.4, 2.4, 0.08]} />
        <meshStandardMaterial color="#0d1626" />
      </mesh>
      <Html transform position={[0, 1.9, 0.06]} distanceFactor={4.2} occlude={false}>
        <div className="tablica">
          <div className="tablica-tytul">TRADER COMPANY</div>
          {stan && (
            <div className="tablica-wiersz">
              <span>Budget <b>{usd(stan.budzet)}</b> ({procent(stan.wynik_procent)})</span>
              <span>Open positions <b>{stan.otwarte_pozycje.length}</b></span>
            </div>
          )}
          {iteracja && <div className="tablica-wiersz przygaszony">Iteration {zakresSwiecy(iteracja.czas_swiecy)}</div>}
          {runda ? (
            <div className="tablica-para">Now discussing: <b>{runda.symbol}</b>
              {krok?.typ === "wynik" && <> → {runda.glosowanie?.tak} YES / {runda.glosowanie?.nie} NO</>}
            </div>
          ) : (
            iteracja && (
              <div className="tablica-pary">
                {iteracja.rundy.filter((r) => !r.pominieta).map((r) => (
                  <span key={r.id} className={r.decyzja === "TAK" ? "plus" : "minus"}>
                    {r.symbol.replace("/USDT", "")} {r.glosowanie?.tak}:{r.glosowanie?.nie}
                  </span>
                ))}
              </div>
            )
          )}
        </div>
      </Html>
    </group>
  );
}
