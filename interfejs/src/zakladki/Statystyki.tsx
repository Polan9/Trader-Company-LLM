import { api, StatystykiTransakcji } from "../api";
import { liczbaR, procent, usd } from "../formaty";
import { uzyjDanych } from "../uzyjDanych";

/** Zakładka Statistics — na razie tabele; wykresy w etapie 3. */
export default function Statystyki() {
  const { dane: s, blad } = uzyjDanych(api.statystyki);
  if (blad) return <div className="blad">{blad}</div>;
  if (!s) return <div className="przygaszony">Loading…</div>;

  return (
    <div className="statystyki">
      <div className="kafelki">
        <Kafelek tytul="Bench trades" s={s.lawa} />
        <Kafelek tytul="Always enter (reference)" s={s.zawsze_wchodz} />
        <Kafelek tytul="RSI/MACD heuristic" s={s.heurystyka} />
        <div className="karta kafelek">
          <h3>Buy & hold</h3>
          <div>BTC: <b>{procent(s.kup_i_trzymaj_btc?.netto_procent)}</b> net</div>
          <div>Analysed pairs: <b>{procent(s.kup_i_trzymaj_pary.length
            ? s.kup_i_trzymaj_pary.reduce((suma, p) => suma + p.netto_procent, 0) / s.kup_i_trzymaj_pary.length
            : null)}</b> avg net</div>
          <div className="przygaszony">Max drawdown {procent(s.maks_spadek_procent)}</div>
        </div>
      </div>

      <div className="karta">
        <h3>Trader scorecard</h3>
        <table>
          <thead>
            <tr><th>Trader</th><th>Votes</th><th>YES %</th><th>Resolved</th><th>Accuracy</th><th>YES acc.</th><th>NO acc.</th><th>Avg R (YES)</th><th>Avg confidence</th></tr>
          </thead>
          <tbody>
            {s.karta_traderow.map((w) => (
              <tr key={w.trader}>
                <td>{w.trader}</td><td>{w.glosy}</td><td>{w.tak_procent.toFixed(0)}%</td><td>{w.rozstrzygniete}</td>
                <td>{w.trafnosc_procent === null ? "—" : `${w.trafnosc_procent.toFixed(0)}%`}</td>
                <td>{w.trafnosc_tak_procent === null ? "—" : `${w.trafnosc_tak_procent.toFixed(0)}%`}</td>
                <td>{w.trafnosc_nie_procent === null ? "—" : `${w.trafnosc_nie_procent.toFixed(0)}%`}</td>
                <td>{liczbaR(w.sredni_r_tak)}</td>
                <td>{w.srednia_pewnosc === null ? "—" : w.srednia_pewnosc.toFixed(0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="karta">
        <h3>Accuracy by declared confidence</h3>
        <div className="przygaszony">Does a trader's confidence mean anything? For NO votes, avg R is the reference trade result (negative = the NO avoided a loss).</div>
        <table>
          <thead><tr><th>Vote</th><th>Confidence</th><th>Resolved</th><th>Accuracy</th><th>Avg R</th></tr></thead>
          <tbody>
            {s.trafnosc_wg_pewnosci.filter((w) => w.liczba > 0).map((w) => (
              <tr key={`${w.glos}${w.przedzial}`}>
                <td className={w.glos === "TAK" ? "plus" : "minus"}>{w.glos === "TAK" ? "YES" : "NO"}</td>
                <td>{w.przedzial}</td><td>{w.liczba}</td>
                <td>{w.trafnosc_procent === null ? "—" : `${w.trafnosc_procent.toFixed(0)}%`}</td>
                <td>{liczbaR(w.sredni_r)}</td>
              </tr>
            ))}
            {s.trafnosc_wg_pewnosci.every((w) => w.liczba === 0) && (
              <tr><td colSpan={5} className="przygaszony">No resolved votes with confidence yet (field added 2026-10-25).</td></tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="karta">
        <h3>LLM cost per day</h3>
        <table>
          <thead><tr><th>Day</th><th>Rounds</th><th>Cost</th></tr></thead>
          <tbody>
            {s.koszt_llm_dziennie.map((d) => (
              <tr key={d.dzien}><td>{d.dzien}</td><td>{d.rundy}</td><td>{usd(d.koszt_usd, 4)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
      {s.lawa.liczba < 100 && (
        <div className="przygaszony">Fewer than 100 closed trades — results may be random.</div>
      )}
    </div>
  );
}

function Kafelek({ tytul, s }: { tytul: string; s: StatystykiTransakcji }) {
  return (
    <div className="karta kafelek">
      <h3>{tytul}</h3>
      {s.liczba === 0 ? (
        <div className="przygaszony">No resolved trades yet</div>
      ) : (
        <>
          <div>Trades <b>{s.liczba}</b> · win rate <b>{s.skutecznosc_procent?.toFixed(1)}%</b></div>
          <div>Avg <b>{liczbaR(s.sredni_r)}</b> · total <b>{liczbaR(s.suma_r)}</b></div>
          <div className="przygaszony">Profit factor {s.profit_factor === null || s.profit_factor === undefined ? "∞" : s.profit_factor.toFixed(2)}</div>
        </>
      )}
    </div>
  );
}
