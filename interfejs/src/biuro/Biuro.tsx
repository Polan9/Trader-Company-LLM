import { ReactNode } from "react";
import { Float } from "@react-three/drei";
import { Lawa, Stan, SzczegolyIteracji } from "../api";
import { cena, usd } from "../formaty";
import { Biurko, Krzeslo, Podlogi, Roslina, StolOwalny } from "./Meble";
import { aktywnyAktor, glosyDoTejPory, Krok } from "./odtwarzanie";
import Postac from "./Postac";
import Przeplyw from "./Przeplyw";
import Sciany from "./Sciany";
import Tablica from "./Tablica";
import {
  KOLORY, miejscePrzyStole, PERSONEL, SALA, SRODEK_HEAD_TRADERA, STANOWISKO_HEAD_TRADERA, V3, X_POKOI,
} from "./uklad";

export type Wybor = { typ: "trader"; id: string } | { typ: "personel"; rola: string } | { typ: "head_trader" };

const KOSZULE_TRADEROW = ["#3d7bd9", "#d9a23d", "#9a4dd9", "#3db8a0", "#d94d7a", "#7ad94d"];
const tak = (glos: string) => (glos === "TAK" ? "YES" : "NO");
const bezUsdt = (symbol: string) => symbol.replace("/USDT", "");

interface Wlasciwosci {
  lawa: Lawa | null;
  stan: Stan | null;
  iteracja: SzczegolyIteracji | null;
  kroki: Krok[];
  indeks: number | null;
  onWybierz: (wybor: Wybor) => void;
}

/** Cała makieta: pokoje, meble, postacie, tablica i przepływy danych dla bieżącego kroku odtwarzania. */
export default function Biuro({ lawa, stan, iteracja, kroki, indeks, onWybierz }: Wlasciwosci) {
  const krok = indeks === null ? null : kroki[indeks];
  const aktor = aktywnyAktor(krok);
  const runda = krok && "runda" in krok ? krok.runda : null;
  const glosyTeraz = glosyDoTejPory(kroki, indeks);
  const rundy = (iteracja?.rundy ?? []).filter((r) => !r.pominieta);
  const traderzy = lawa?.traderzy ?? [];
  const pozycjaPersonelu = (rola: string) => PERSONEL.find((p) => p.rola === rola)!.pozycja;

  const swiatloStolu = krok?.typ === "wynik" ? (krok.runda.decyzja === "TAK" ? KOLORY.tak : KOLORY.nie) : null;

  return (
    <Float speed={1.2} rotationIntensity={0.03} floatIntensity={0.25} floatingRange={[-0.1, 0.1]}>
      <Podlogi />
      <Sciany />
      <StolOwalny swiatlo={swiatloStolu} />
      <Tablica stan={stan} iteracja={iteracja} krok={krok} />
      <Roslina pozycja={[-SALA / 2 + 0.8, 0, -SALA / 2 + 0.8]} />
      <Roslina pozycja={[-SALA / 2 + 0.8, 0, SALA / 2 - 0.8]} />
      <Roslina pozycja={[X_POKOI + 3.2, 0, -7.2]} />

      {/* Traderzy przy owalnym stole */}
      {traderzy.map((t, i) => {
        const { pozycja, obrot } = miejscePrzyStole(i, traderzy.length);
        const oddaleniePozycji: V3 = [pozycja[0] * 1.08, 0, pozycja[2] * 1.08]; // krzesło za postacią
        const opinieIteracji = rundy.flatMap((r) => r.opinie.filter((o) => o.trader_id === t.id).map((o) => ({ r, o })));
        let kolorStatusu: string | null;
        let dymek: ReactNode = null;
        if (!t.aktywny) {
          kolorStatusu = KOLORY.nieaktywny;
          dymek = krok ? null : <span className="przygaszony">inactive</span>;
        } else if (runda) {
          const glos = glosyTeraz.get(t.id);
          kolorStatusu = glos ? (glos.glos === "TAK" ? KOLORY.tak : KOLORY.nie) : KOLORY.brak;
          if (glos) {
            dymek = (
              <>
                <b className={glos.glos === "TAK" ? "plus" : "minus"}>{tak(glos.glos)}</b>
                {glos.glos === "TAK" && <> · SL {cena(glos.stop_loss)} · TP {cena(glos.take_profit)}</>}
                {aktor === t.id && <div className="dymek-uzasadnienie">{glos.uzasadnienie.length > 260 ? `${glos.uzasadnienie.slice(0, 260)}…` : glos.uzasadnienie}</div>}
              </>
            );
          }
        } else {
          const ileTak = opinieIteracji.filter(({ o }) => o.glos === "TAK").length;
          kolorStatusu = opinieIteracji.length === 0 ? KOLORY.brak : ileTak > 0 ? KOLORY.tak : KOLORY.nie;
          dymek = opinieIteracji.length ? (
            opinieIteracji.map(({ r, o }) => (
              <span key={r.id} className={o.glos === "TAK" ? "plus" : "minus"}>{bezUsdt(r.symbol)} {tak(o.glos)} </span>
            ))
          ) : null;
        }
        return (
          <group key={t.id}>
            <Krzeslo pozycja={oddaleniePozycji} obrot={obrot} />
            <Postac pozycja={pozycja} obrot={obrot} kolorKoszuli={KOSZULE_TRADEROW[i % KOSZULE_TRADEROW.length]}
              kolorStatusu={kolorStatusu} aktywna={aktor === t.id} przygaszona={!t.aktywny}
              podpis={t.nazwa} dymek={dymek} onKlik={() => onWybierz({ typ: "trader", id: t.id })} />
          </group>
        );
      })}

      {/* Gabinet Head Tradera */}
      <Biurko pozycja={STANOWISKO_HEAD_TRADERA} aktywne={aktor === "head_trader"} ekran={KOLORY.akcent} />
      <Krzeslo pozycja={[STANOWISKO_HEAD_TRADERA[0], 0, STANOWISKO_HEAD_TRADERA[2] - 0.9]} obrot={0} kolor="#4a3b2a" />
      <Postac pozycja={[STANOWISKO_HEAD_TRADERA[0], 0, STANOWISKO_HEAD_TRADERA[2] - 0.75]} kolorKoszuli={KOLORY.akcent}
        kolorStatusu={null} aktywna={aktor === "head_trader"}
        podpis={`Head Trader${lawa ? `\n${lawa.head_trader.model}` : ""}`}
        dymek={dymekHeadTradera(krok, rundy)} onKlik={() => onWybierz({ typ: "head_trader" })} />

      {/* Pokój personelu: Screener, Risk Manager, Researcher, Execution */}
      {PERSONEL.map((p) => (
        <group key={p.rola}>
          <Biurko pozycja={p.pozycja} obrot={Math.PI} aktywne={aktor === p.rola} ekran={p.kolor} />
          <Krzeslo pozycja={[p.pozycja[0], 0, p.pozycja[2] + 0.9]} obrot={Math.PI} />
          <Postac pozycja={[p.pozycja[0], 0, p.pozycja[2] + 0.75]} obrot={Math.PI} kolorKoszuli={p.kolor}
            kolorStatusu={null} aktywna={aktor === p.rola} przygaszona={p.rola === "researcher"} podpis={p.nazwa}
            dymek={dymekPersonelu(p.rola, krok, iteracja, stan)} onKlik={() => onWybierz({ typ: "personel", rola: p.rola })} />
        </group>
      ))}

      {/* Przepływy danych w bieżącym kroku */}
      {krok?.typ === "para" && <Przeplyw od={pozycjaPersonelu("screener")} do={[0, 0, 0]} />}
      {krok?.typ === "head_trader" && <Przeplyw od={[0, 0, 0]} do={SRODEK_HEAD_TRADERA} kolor={KOLORY.tak} />}
      {krok?.typ === "risk_manager" && <Przeplyw od={SRODEK_HEAD_TRADERA} do={pozycjaPersonelu("risk_manager")} kolor={KOLORY.tak} />}
    </Float>
  );
}

function dymekHeadTradera(krok: Krok | null, rundy: SzczegolyIteracji["rundy"]): ReactNode {
  if (krok?.typ === "head_trader") {
    const ht = krok.runda.head_trader;
    return ht?.stop_loss ? <>SL {cena(ht.stop_loss)} · TP {cena(ht.take_profit)} <span className="przygaszony">({ht.zrodlo})</span></> : "Deciding…";
  }
  if (krok) return null;
  const zDecyzja = rundy.find((r) => r.head_trader?.stop_loss);
  if (zDecyzja?.head_trader) return <>{zDecyzja.symbol}: SL {cena(zDecyzja.head_trader.stop_loss)} · TP {cena(zDecyzja.head_trader.take_profit)}</>;
  return <span className="przygaszony">Waiting — no YES majority</span>;
}

function dymekPersonelu(rola: string, krok: Krok | null, iteracja: SzczegolyIteracji | null, stan: Stan | null): ReactNode {
  const ranking = iteracja?.screener?.ranking ?? [];
  if (rola === "screener") {
    if (krok?.typ === "screener") return <>Ranking: {ranking.slice(0, 5).map((p) => bezUsdt(p.symbol)).join(", ")}</>;
    if (krok?.typ === "para") return <>→ <b>{krok.runda.symbol}</b></>;
    if (krok) return null;
    return iteracja?.screener?.symbol ? <>Picked <b>{bezUsdt(iteracja.screener.symbol)}</b> + {Math.max(0, ranking.length - 1)} more</> : null;
  }
  if (rola === "risk_manager") {
    if (krok?.typ === "risk_manager") {
      const d = krok.runda.decyzja_koncowa as { otworz_pozycje?: boolean; wielkosc_usd?: number; powody?: string[] } | null;
      return d?.otworz_pozycje ? <span className="plus">Approved {usd(d.wielkosc_usd)}</span> : <span className="minus">VETO</span>;
    }
    if (krok) return null;
    return <span className="przygaszony">No trades to check</span>;
  }
  if (rola === "execution") {
    if (krok?.typ === "risk_manager" && krok.runda.otworz_pozycje) return <>Opening position (simulation)</>;
    if (krok) return null;
    return stan ? <span className="przygaszony">Simulation · {stan.otwarte_pozycje.length} open</span> : null;
  }
  return krok ? null : <span className="przygaszony">News module coming soon</span>;
}
