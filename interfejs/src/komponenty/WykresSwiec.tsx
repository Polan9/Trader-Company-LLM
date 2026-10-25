import { useEffect, useRef, useState } from "react";
import { createChart, CrosshairMode, LineStyle, UTCTimestamp } from "lightweight-charts";
import { api, Swieca } from "../api";

export interface Poziom {
  cena: number;
  kolor: string;
  etykieta: string;
}

/** Wykres świec pary wokół chwili decyzji, z poziomami (wejście, SL, TP) i znacznikiem świecy decyzji. */
export default function WykresSwiec({ symbol, wokolMs, poziomy }: { symbol: string; wokolMs: number; poziomy: Poziom[] }) {
  const kontener = useRef<HTMLDivElement>(null);
  const [swiece, ustawSwiece] = useState<Swieca[] | null>(null);
  const [blad, ustawBlad] = useState<string | null>(null);

  useEffect(() => {
    ustawSwiece(null);
    api.swiece(symbol, wokolMs).then(ustawSwiece).catch((e: Error) => ustawBlad(e.message));
  }, [symbol, wokolMs]);

  useEffect(() => {
    if (!kontener.current || !swiece) return;
    const wykres = createChart(kontener.current, {
      height: 280,
      layout: { background: { color: "transparent" }, textColor: "#a8b3c7" },
      grid: { vertLines: { color: "#1f2a3d" }, horzLines: { color: "#1f2a3d" } },
      crosshair: { mode: CrosshairMode.Normal },
      timeScale: { timeVisible: true, secondsVisible: false },
      autoSize: true,
    });
    const seria = wykres.addCandlestickSeries({
      upColor: "#26a69a", downColor: "#ef5350", borderVisible: false,
      wickUpColor: "#26a69a", wickDownColor: "#ef5350",
      priceFormat: { type: "price", precision: 6, minMove: 0.000001 },
    });
    seria.setData(swiece.map((s) => ({ time: s.czas as UTCTimestamp, open: s.open, high: s.high, low: s.low, close: s.close })));
    for (const p of poziomy) {
      seria.createPriceLine({ price: p.cena, color: p.kolor, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: p.etykieta });
    }
    seria.setMarkers([{ time: Math.floor(wokolMs / 1000) as UTCTimestamp, position: "aboveBar", color: "#f5c542", shape: "arrowDown", text: "decision" }]);
    wykres.timeScale().fitContent();
    return () => wykres.remove();
  }, [swiece, poziomy, wokolMs]);

  if (blad) return <div className="blad">Chart: {blad}</div>;
  if (!swiece) return <div className="przygaszony">Loading chart…</div>;
  return <div ref={kontener} className="wykres" />;
}
