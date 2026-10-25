import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { CameraControls } from "@react-three/drei";
import { api, SzczegolyIteracji } from "../api";
import Biuro, { Wybor } from "../biuro/Biuro";
import { uzyjOdtwarzania, zbudujKroki } from "../biuro/odtwarzanie";
import { WIDOKI } from "../biuro/uklad";
import { cena, liczbaR, usd, zakresSwiecy } from "../formaty";
import { uzyjDanych } from "../uzyjDanych";

const ODSWIEZANIE_STANU_MS = 15_000; // jak szybko zauważamy nową iterację
const KLUCZ_AUTO = "trader-company:auto-odtwarzanie";

function czytajAuto(): boolean {
  try {
    return localStorage.getItem(KLUCZ_AUTO) !== "nie";
  } catch {
    return true; // tryb prywatny / zablokowana pamięć — domyślnie włączone
  }
}

/** Zakładka Preview — makieta biura 3D z odtwarzaniem iteracji; nowa iteracja odtwarza się sama. */
export default function Podglad() {
  const { dane: lawa } = uzyjDanych(api.lawa);
  const { dane: stan } = uzyjDanych(api.stan, [], ODSWIEZANIE_STANU_MS);
  const idIteracji = stan?.ostatnia_iteracja_ms ?? null;
  const kompletna = stan?.ostatnia_iteracja_kompletna ?? false;
  // Iteracja pobierana razem z informacją, czy w chwili pobrania była już kompletna
  const { dane: paczka } = uzyjDanych<{ iteracja: SzczegolyIteracji; kompletna: boolean } | null>(
    () => (idIteracji ? api.iteracja(idIteracji).then((iteracja) => ({ iteracja, kompletna })) : Promise.resolve(null)),
    [idIteracji, kompletna],
  );
  const iteracja = paczka?.iteracja ?? null;
  const kroki = useMemo(() => (iteracja ? zbudujKroki(iteracja) : []), [iteracja]);
  const odtwarzanie = uzyjOdtwarzania(kroki);
  const [wybor, ustawWybor] = useState<Wybor | null>(null);
  const [auto, ustawAuto] = useState(czytajAuto);
  const ostatnioOdtworzona = useRef<number | null>(null);
  const kamera = useRef<CameraControls>(null);

  const ustawWidok = (klucz: string) => {
    const w = WIDOKI[klucz];
    kamera.current?.setLookAt(...w.pozycja, ...w.cel, true);
  };

  const przelaczAuto = () => {
    ustawAuto(!auto);
    try {
      localStorage.setItem(KLUCZ_AUTO, auto ? "nie" : "tak");
    } catch {
      /* brak pamięci przeglądarki — ustawienie działa do odświeżenia strony */
    }
  };

  // Nowa, kompletna iteracja → odtwórz automatycznie. Przy pierwszym wejściu na stronę tylko zapamiętujemy.
  useEffect(() => {
    if (!paczka?.kompletna) return;
    const id = paczka.iteracja.id;
    if (ostatnioOdtworzona.current === null) {
      ostatnioOdtworzona.current = id;
      return;
    }
    if (id === ostatnioOdtworzona.current) return;
    ostatnioOdtworzona.current = id;
    if (auto) {
      odtwarzanie.graj();
      ustawWidok("ogolny");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paczka]);

  return (
    <div className="podglad">
      <Canvas shadows dpr={[1, 2]} camera={{ position: WIDOKI.ogolny.pozycja, fov: 45 }}
        onPointerMissed={() => ustawWybor(null)}>
        <color attach="background" args={["#0b1220"]} />
        <hemisphereLight args={["#e8f0ff", "#3a4150", 1.1]} />
        <directionalLight position={[12, 22, 14]} intensity={1.8} castShadow shadow-mapSize={[2048, 2048]}
          shadow-camera-left={-20} shadow-camera-right={20} shadow-camera-top={20} shadow-camera-bottom={-20} />
        <Biuro lawa={lawa} stan={stan} iteracja={iteracja} kroki={kroki} indeks={odtwarzanie.indeks} onWybierz={ustawWybor} />
        <CameraControls ref={kamera} makeDefault minDistance={6} maxDistance={70} maxPolarAngle={Math.PI / 2.15} />
      </Canvas>

      <div className="podglad-przyciski">
        {Object.entries(WIDOKI).map(([klucz, w]) => (
          <button key={klucz} className="zakladka" onClick={() => ustawWidok(klucz)}>{w.etykieta}</button>
        ))}
        {odtwarzanie.indeks === null ? (
          <button className="zakladka aktywna" disabled={!iteracja} onClick={() => { odtwarzanie.graj(); ustawWidok("ogolny"); }}>
            ▶ Replay last iteration
          </button>
        ) : (
          <button className="zakladka aktywna" onClick={odtwarzanie.zatrzymaj}>
            ■ Stop ({odtwarzanie.indeks + 1}/{odtwarzanie.liczbaKrokow})
          </button>
        )}
        <button className={auto ? "zakladka aktywna" : "zakladka"} onClick={przelaczAuto}
          title="Play each new iteration automatically when the simulator finishes it">
          Auto-replay: {auto ? "on" : "off"}
        </button>
      </div>

      {iteracja && (
        <div className="podglad-info przygaszony">
          {odtwarzanie.indeks === null ? "Last" : "Replaying"} iteration {zakresSwiecy(iteracja.czas_swiecy)}
          {!kompletna && " · simulator is still working on it…"}
        </div>
      )}

      {wybor && <PanelWyboru wybor={wybor} iteracja={iteracja} onZamknij={() => ustawWybor(null)}
        nazwaTradera={(id) => lawa?.traderzy.find((t) => t.id === id)?.nazwa ?? id} />}
      <div className="podpowiedz przygaszony">Drag to rotate · scroll / pinch to zoom · right-drag / two fingers to pan · click a person</div>
    </div>
  );
}

function PanelWyboru({ wybor, iteracja, onZamknij, nazwaTradera }:
  { wybor: Wybor; iteracja: SzczegolyIteracji | null; onZamknij: () => void; nazwaTradera: (id: string) => string }) {
  const rundy = (iteracja?.rundy ?? []).filter((r) => !r.pominieta);
  let tytul = "";
  let tresc: JSX.Element;

  if (wybor.typ === "trader") {
    tytul = nazwaTradera(wybor.id);
    const opinie = rundy.flatMap((r) => r.opinie.filter((o) => o.trader_id === wybor.id).map((o) => ({ r, o })));
    tresc = opinie.length === 0 ? <div className="przygaszony">No votes in the last iteration (inactive or skipped).</div> : (
      <>
        {opinie.map(({ r, o }) => {
          const ocena = r.oceny.find((x) => x.kto === o.trader_id);
          return (
            <div key={r.id} className="opinia-krotka">
              <b className={o.glos === "TAK" ? "plus" : "minus"}>{r.symbol}: {o.glos === "TAK" ? "YES" : "NO"}</b>
              {o.pewnosc !== null && <span className="przygaszony"> · confidence {o.pewnosc.toFixed(0)}</span>}
              {o.glos === "TAK" && <div className="przygaszony">SL {cena(o.stop_loss)} · TP {cena(o.take_profit)} · size {o.skala_pozycji}%
                {ocena && <> · {ocena.status === "zamknieta" ? `${ocena.powod} ${liczbaR(ocena.wynik_r)}` : "open"}</>}</div>}
              <p>{o.uzasadnienie}</p>
              {o.uwagi.map((u) => <div key={u} className="uwaga">⚠ {u}</div>)}
            </div>
          );
        })}
      </>
    );
  } else if (wybor.typ === "head_trader") {
    tytul = "Head Trader";
    const zDecyzja = rundy.filter((r) => r.head_trader?.stop_loss);
    tresc = zDecyzja.length === 0
      ? <div className="przygaszony">Not called in the last iteration — the bench had no YES majority.</div>
      : <>{zDecyzja.map((r) => (
        <div key={r.id} className="opinia-krotka">
          <b>{r.symbol}</b>: SL {cena(r.head_trader!.stop_loss)} · TP {cena(r.head_trader!.take_profit)} ({r.head_trader!.zrodlo})
          <p>{r.head_trader!.uzasadnienie}</p>
        </div>))}</>;
  } else if (wybor.rola === "screener") {
    tytul = "Screener";
    tresc = iteracja?.screener ? (
      <>
        <table>
          <thead><tr><th>#</th><th>Pair</th><th>Cost/ATR</th><th>ATR</th></tr></thead>
          <tbody>{iteracja.screener.ranking.map((p, i) => (
            <tr key={p.symbol}><td>{i + 1}</td><td>{p.symbol}</td><td>{p.koszt_do_atr.toFixed(1)}%</td><td>{p.atr_procent.toFixed(2)}%</td></tr>
          ))}</tbody>
        </table>
        <div className="przygaszony">Rejected: {iteracja.screener.odrzucone.length} pairs</div>
      </>
    ) : <div className="przygaszony">No screener data.</div>;
  } else if (wybor.rola === "risk_manager") {
    tytul = "Risk Manager";
    const sprawdzone = rundy.filter((r) => r.decyzja === "TAK");
    tresc = sprawdzone.length === 0 ? <div className="przygaszony">Nothing to check — no YES majority in the last iteration.</div> : (
      <>{sprawdzone.map((r) => {
        const d = r.decyzja_koncowa as { otworz_pozycje?: boolean; wielkosc_usd?: number; ryzyko_usd?: number; powody?: string[] } | null;
        return <div key={r.id} className="opinia-krotka"><b>{r.symbol}</b>: {d?.otworz_pozycje
          ? <span className="plus">approved {usd(d.wielkosc_usd)} (risk {usd(d.ryzyko_usd)})</span>
          : <span className="minus">{d?.powody?.join("; ")}</span>}</div>;
      })}</>
    );
  } else if (wybor.rola === "execution") {
    tytul = "Execution";
    tresc = <div className="przygaszony">Simulation mode — orders are not sent to the exchange yet.</div>;
  } else {
    tytul = "Researcher";
    tresc = <div className="przygaszony">News module (RSS, Fear & Greed, LLM rating) is not implemented yet.</div>;
  }

  return (
    <div className="panel-osoby karta">
      <button className="zamknij" onClick={onZamknij}>×</button>
      <h3>{tytul}</h3>
      {tresc}
    </div>
  );
}
