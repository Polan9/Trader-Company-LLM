import { useMemo, useState } from "react";
import { api, Iteracja, Runda, SzczegolyIteracji } from "../api";
import WykresSwiec, { Poziom } from "../komponenty/WykresSwiec";
import { cena, liczbaR, procent, usd, zakresSwiecy } from "../formaty";
import { uzyjDanych } from "../uzyjDanych";

/** Zakładka Reports: lista iteracji (świec) i podgląd wybranej iteracji. */
export default function Raporty() {
  const { dane: iteracje, blad } = uzyjDanych(() => api.iteracje(100));
  const [wybrana, ustawWybrana] = useState<number | null>(null);
  const idWybranej = wybrana ?? iteracje?.[0]?.id ?? null;

  return (
    <div className="raporty">
      <aside className="lista-iteracji">
        <h2>Iterations</h2>
        {blad && <div className="blad">{blad}</div>}
        {iteracje?.map((it) => (
          <PozycjaListy key={it.id} iteracja={it} aktywna={it.id === idWybranej} onWybierz={() => ustawWybrana(it.id)} />
        ))}
      </aside>
      <section className="podglad-iteracji">
        {idWybranej !== null ? <PodgladIteracji id={idWybranej} /> : <div className="przygaszony">No iterations yet.</div>}
      </section>
    </div>
  );
}

function PozycjaListy({ iteracja, aktywna, onWybierz }: { iteracja: Iteracja; aktywna: boolean; onWybierz: () => void }) {
  const otwarto = iteracja.rundy.some((r) => r.otworz_pozycje);
  const pominieta = iteracja.rundy.every((r) => r.pominieta);
  return (
    <button className={aktywna ? "iteracja aktywna" : "iteracja"} onClick={onWybierz}>
      <div className="iteracja-czas">
        {zakresSwiecy(iteracja.czas_swiecy)}
        {otwarto && <span className="znaczek tak">OPENED</span>}
        {pominieta && <span className="znaczek">SKIPPED</span>}
      </div>
      <div className="iteracja-pary">
        {iteracja.rundy.filter((r) => !r.pominieta).map((r) => (
          <span key={r.id} className={r.decyzja === "TAK" ? "para tak" : "para"}>
            {r.symbol.replace("/USDT", "")} {r.tak}:{r.nie}
          </span>
        ))}
      </div>
      <div className="przygaszony">{usd(iteracja.koszt_llm_usd, 4)}</div>
    </button>
  );
}

function PodgladIteracji({ id }: { id: number }) {
  const { dane: it, blad } = uzyjDanych<SzczegolyIteracji>(() => api.iteracja(id), [id]);
  const [indeks, ustawIndeks] = useState(0);
  if (blad) return <div className="blad">{blad}</div>;
  if (!it || it.id !== id) return <div className="przygaszony">Loading…</div>;
  const rundy = it.rundy.filter((r) => !r.pominieta);
  const runda = rundy[Math.min(indeks, rundy.length - 1)];

  return (
    <div>
      <h2>Iteration {zakresSwiecy(it.czas_swiecy)} <span className="przygaszony">· LLM {usd(it.koszt_llm_usd, 4)}</span></h2>
      {it.screener && (
        <div className="karta">
          <h3>Screener ranking</h3>
          <table>
            <thead><tr><th>#</th><th>Pair</th><th>Cost / ATR</th><th>ATR</th><th>Spread</th><th>Volume 24h</th></tr></thead>
            <tbody>
              {it.screener.ranking.map((p, i) => (
                <tr key={p.symbol}>
                  <td>{i + 1}</td><td>{p.symbol}</td><td>{p.koszt_do_atr.toFixed(1)}%</td><td>{p.atr_procent.toFixed(2)}%</td>
                  <td>{p.spread_procent.toFixed(4)}%</td><td>{(p.wolumen_usdt_24h / 1e6).toFixed(0)}M</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="przygaszony">Rejected: {it.screener.odrzucone.length} pairs</div>
        </div>
      )}
      {rundy.length === 0 && <div className="karta">{it.rundy[0]?.powody.join("; ")}</div>}
      {rundy.length > 0 && (
        <>
          <div className="przelacznik-par">
            {rundy.map((r, i) => (
              <button key={r.id} className={r.id === runda.id ? "zakladka aktywna" : "zakladka"} onClick={() => ustawIndeks(i)}>
                {r.symbol} · {r.glosowanie?.tak}:{r.glosowanie?.nie}
              </button>
            ))}
          </div>
          <PodgladRundy runda={runda} czasMs={it.id} />
        </>
      )}
    </div>
  );
}

function PodgladRundy({ runda, czasMs }: { runda: Runda; czasMs: number }) {
  const poziomy = useMemo<Poziom[]>(() => {
    const wynik: Poziom[] = [];
    if (runda.cena_wejscia) wynik.push({ cena: runda.cena_wejscia, kolor: "#f5c542", etykieta: "entry" });
    const ref = runda.oceny.find((o) => o.kto === "referencja");
    if (ref) {
      wynik.push({ cena: ref.stop_loss, kolor: "#ef5350", etykieta: "ref SL" });
      wynik.push({ cena: ref.take_profit, kolor: "#26a69a", etykieta: "ref TP" });
    }
    return wynik;
  }, [runda]);

  const a = runda.analiza;
  return (
    <div className="runda">
      <div className="karta">
        <h3>
          {runda.symbol} — bench says <span className={runda.decyzja === "TAK" ? "plus" : "minus"}>{runda.decyzja === "TAK" ? "YES" : "NO"}</span>
          {runda.otworz_pozycje && <span className="znaczek tak">POSITION OPENED</span>}
        </h3>
        <div className="przygaszony">{runda.powody.join("; ")}</div>
        <WykresSwiec symbol={runda.symbol} wokolMs={czasMs} poziomy={poziomy} />
        {a && (
          <div className="wskazniki">
            <span>Entry <b>{cena(runda.cena_wejscia)}</b></span>
            <span>RSI <b>{a.rsi.wartosc.toFixed(1)}</b> ({a.rsi.strefa})</span>
            <span>ATR <b>{a.atr.procent_ceny.toFixed(2)}%</b></span>
            <span>Volume vs avg <b>{procent(a.wolumen.zmiana_procent_vs_srednia, 0)}</b></span>
            <span>Z-score <b>{a.statystyki.zscore_ceny.toFixed(2)}</b></span>
            <span>Range position <b>{a.statystyki.pozycja_w_zakresie.toFixed(0)}</b></span>
            <span>Autocorr <b>{a.statystyki.autokorelacja_lag1.toFixed(3)}</b></span>
            <span>Cost <b>{runda.koszt_procent?.toFixed(3)}%</b></span>
            <span>MACD <b>{a.macd.interpretacja}</b></span>
          </div>
        )}
      </div>

      <div className="opinie">
        {runda.opinie.map((o) => {
          const ocena = runda.oceny.find((x) => x.kto === o.trader_id);
          return (
            <div key={o.trader_id} className={o.glos === "TAK" ? "karta opinia tak" : "karta opinia"}>
              <div className="opinia-naglowek">
                <b>{o.nazwa}</b> <span className="przygaszony">{o.model}</span>
                <span className={o.glos === "TAK" ? "glos tak" : "glos nie"}>{o.glos === "TAK" ? "YES" : "NO"}</span>
              </div>
              {o.glos === "TAK" && (
                <div className="przygaszony">
                  SL {cena(o.stop_loss)} · TP {cena(o.take_profit)} · size {o.skala_pozycji}%
                  {ocena && <> · outcome: {ocena.status === "zamknieta" ? `${ocena.powod} ${liczbaR(ocena.wynik_r)}` : "open"}</>}
                </div>
              )}
              <p>{o.uzasadnienie}</p>
              {o.uwagi.map((u) => <div key={u} className="uwaga">⚠ {u}</div>)}
            </div>
          );
        })}
      </div>

      {(runda.head_trader?.stop_loss || runda.pozycja) && (
        <div className="karta">
          <h3>Head Trader & Risk Manager</h3>
          {runda.head_trader?.stop_loss && (
            <p>SL {cena(runda.head_trader.stop_loss)} · TP {cena(runda.head_trader.take_profit)} ({runda.head_trader.zrodlo}) — {runda.head_trader.uzasadnienie}</p>
          )}
          {runda.pozycja && (
            <p>Position: {usd(runda.pozycja.wielkosc_usd)} · risk {usd(runda.pozycja.ryzyko_usd)} · status {runda.pozycja.status}
              {runda.pozycja.wynik_usd !== null && <> · result {usd(runda.pozycja.wynik_usd)} ({liczbaR(runda.pozycja.wynik_r)})</>}</p>
          )}
        </div>
      )}

      <div className="karta">
        <h3>Evaluations (hypothetical trades)</h3>
        <table>
          <thead><tr><th>Who</th><th>Entry</th><th>SL</th><th>TP</th><th>Status</th><th>Result</th></tr></thead>
          <tbody>
            {runda.oceny.map((o) => (
              <tr key={o.id}>
                <td>{o.kto === "referencja" ? "reference" : runda.opinie.find((x) => x.trader_id === o.kto)?.nazwa ?? o.kto}</td>
                <td>{cena(o.cena_wejscia)}</td><td>{cena(o.stop_loss)}</td><td>{cena(o.take_profit)}</td>
                <td>{o.status === "zamknieta" ? o.powod : "open"}</td>
                <td className={(o.wynik_r ?? 0) >= 0 ? "plus" : "minus"}>{o.status === "zamknieta" ? `${procent(o.wynik_procent)} (${liczbaR(o.wynik_r)})` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
