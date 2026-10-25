import { useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { Billboard, Float, OrbitControls, Text } from "@react-three/drei";
import { api, Opinia } from "../api";
import { uzyjDanych } from "../uzyjDanych";

// Wymiary makiety (jednostki sceny ≈ metry)
const SALA = 16; // główny pokój: kwadrat SALA × SALA, środek w (0, 0)
const POKOJ = SALA / 2; // dwa pokoje po prawej: każdy SALA/2 × SALA/2
const WYSOKOSC_SCIANY = 1.2; // niskie ściany — widok jak w makiecie
const STOL = { polosX: 4.2, polosZ: 2.2 };
const MIEJSCA = { polosX: 5.6, polosZ: 3.6 };

const KOLOR = { tak: "#26a69a", nie: "#ef5350", brak: "#6b7a90", nieaktywny: "#3a4558" };

interface Osoba {
  id: string;
  nazwa: string;
  aktywny: boolean;
  glosy: { symbol: string; glos: string }[];
  opinie: Opinia[];
}

/** Zakładka Preview — makieta biura 3D. Etap 1: układ pokoi i ostatnie głosy; animacje w kolejnych etapach. */
export default function Podglad() {
  const { dane: lawa } = uzyjDanych(api.lawa);
  const { dane: stan } = uzyjDanych(api.stan);
  const idIteracji = stan?.ostatnia_iteracja_ms ?? null;
  const { dane: iteracja } = uzyjDanych(
    () => (idIteracji ? api.iteracja(idIteracji) : Promise.resolve(null)),
    [idIteracji],
  );
  const [wybrana, ustawWybrana] = useState<Osoba | null>(null);

  const osoby = useMemo<Osoba[]>(() => {
    if (!lawa) return [];
    return lawa.traderzy.map((t) => {
      const opinie = (iteracja?.rundy ?? []).flatMap((r) => r.opinie.filter((o) => o.trader_id === t.id));
      const glosy = (iteracja?.rundy ?? []).flatMap((r) =>
        r.opinie.filter((o) => o.trader_id === t.id).map((o) => ({ symbol: r.symbol, glos: o.glos })),
      );
      return { id: t.id, nazwa: t.nazwa, aktywny: t.aktywny, glosy, opinie };
    });
  }, [lawa, iteracja]);

  return (
    <div className="podglad">
      <Canvas camera={{ position: [14, 16, 20], fov: 45 }} shadows>
        <color attach="background" args={["#0b1220"]} />
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 20, 10]} intensity={1.1} castShadow />
        <Float speed={1} rotationIntensity={0.05} floatIntensity={0.3}>
          <group position={[-POKOJ / 2, 0, 0]}>
            <Pokoj szerokosc={SALA} glebokosc={SALA} pozycja={[0, 0, 0]} kolor="#1b2638" podpis="Trading room" />
            <StolOwalny />
            {osoby.map((o, i) => (
              <MiejsceTradera key={o.id} osoba={o} kat={(i / osoby.length) * Math.PI * 2} onWybierz={() => ustawWybrana(o)} />
            ))}
            <Pokoj szerokosc={POKOJ} glebokosc={POKOJ} pozycja={[SALA / 2 + POKOJ / 2, 0, -POKOJ / 2]} kolor="#22304a"
              podpis={`Head Trader${lawa ? ` (${lawa.head_trader.model})` : ""}`} />
            <Postac pozycja={[SALA / 2 + POKOJ / 2, 0, -POKOJ / 2]} kolor="#f5c542" podpis="Head Trader" />
            <Pokoj szerokosc={POKOJ} glebokosc={POKOJ} pozycja={[SALA / 2 + POKOJ / 2, 0, POKOJ / 2]} kolor="#1f2c42" podpis="Staff" />
            {["Risk Manager", "Screener", "Researcher", "Execution"].map((nazwa, i) => (
              <Postac key={nazwa} pozycja={[SALA / 2 + 2 + (i % 2) * 4, 0, POKOJ / 2 - 2 + Math.floor(i / 2) * 4]}
                kolor="#8fa3c0" podpis={nazwa} />
            ))}
          </group>
        </Float>
        <OrbitControls makeDefault enableDamping maxPolarAngle={Math.PI / 2.2} minDistance={8} maxDistance={60} />
      </Canvas>

      {wybrana && (
        <div className="panel-osoby karta">
          <button className="zamknij" onClick={() => ustawWybrana(null)}>×</button>
          <h3>{wybrana.nazwa}</h3>
          {!wybrana.aktywny && <div className="przygaszony">Inactive (news module not ready yet)</div>}
          {wybrana.opinie.length === 0 && wybrana.aktywny && <div className="przygaszony">No votes in the last iteration.</div>}
          {wybrana.opinie.map((o, i) => (
            <div key={i} className="opinia-krotka">
              <b className={o.glos === "TAK" ? "plus" : "minus"}>{wybrana.glosy[i]?.symbol}: {o.glos === "TAK" ? "YES" : "NO"}</b>
              <p>{o.uzasadnienie}</p>
            </div>
          ))}
        </div>
      )}
      <div className="podpowiedz przygaszony">Drag to rotate · scroll / pinch to zoom · right-drag to pan · click a trader</div>
    </div>
  );
}

function Pokoj({ szerokosc, glebokosc, pozycja, kolor, podpis }:
  { szerokosc: number; glebokosc: number; pozycja: [number, number, number]; kolor: string; podpis: string }) {
  const grubosc = 0.15;
  const sciany: [number, number, number, number, number][] = [
    // [x, z, szerokość, głębokość] — cztery niskie ściany
    [0, -glebokosc / 2, szerokosc, grubosc, 0],
    [0, glebokosc / 2, szerokosc, grubosc, 0],
    [-szerokosc / 2, 0, grubosc, glebokosc, 0],
    [szerokosc / 2, 0, grubosc, glebokosc, 0],
  ];
  return (
    <group position={pozycja}>
      <mesh receiveShadow position={[0, -0.05, 0]}>
        <boxGeometry args={[szerokosc, 0.1, glebokosc]} />
        <meshStandardMaterial color={kolor} />
      </mesh>
      {sciany.map(([x, z, w, d], i) => (
        <mesh key={i} position={[x, WYSOKOSC_SCIANY / 2, z]} castShadow>
          <boxGeometry args={[w, WYSOKOSC_SCIANY, d]} />
          <meshStandardMaterial color="#2d3b55" transparent opacity={0.85} />
        </mesh>
      ))}
      <Text position={[0, 0.02, -glebokosc / 2 + 0.8]} rotation={[-Math.PI / 2, 0, 0]} fontSize={0.6} color="#a8b3c7">
        {podpis}
      </Text>
    </group>
  );
}

function StolOwalny() {
  return (
    <group>
      <mesh position={[0, 0.75, 0]} scale={[STOL.polosX, 1, STOL.polosZ]} castShadow receiveShadow>
        <cylinderGeometry args={[1, 1, 0.12, 64]} />
        <meshStandardMaterial color="#6d4c33" />
      </mesh>
      <mesh position={[0, 0.35, 0]}>
        <cylinderGeometry args={[0.4, 0.6, 0.7, 24]} />
        <meshStandardMaterial color="#4a3423" />
      </mesh>
    </group>
  );
}

function MiejsceTradera({ osoba, kat, onWybierz }: { osoba: Osoba; kat: number; onWybierz: () => void }) {
  const x = Math.cos(kat) * MIEJSCA.polosX;
  const z = Math.sin(kat) * MIEJSCA.polosZ;
  const tak = osoba.glosy.filter((g) => g.glos === "TAK").length;
  const kolor = !osoba.aktywny ? KOLOR.nieaktywny : osoba.glosy.length === 0 ? KOLOR.brak : tak > 0 ? KOLOR.tak : KOLOR.nie;
  const podsumowanie = osoba.glosy.length ? `${tak} YES / ${osoba.glosy.length - tak} NO` : osoba.aktywny ? "—" : "inactive";
  return (
    <group position={[x, 0, z]} rotation={[0, -kat - Math.PI / 2, 0]}>
      <mesh position={[0, 0.25, 0.4]}>
        <boxGeometry args={[0.8, 0.5, 0.8]} />
        <meshStandardMaterial color="#39465e" />
      </mesh>
      <Postac pozycja={[0, 0.3, 0.4]} kolor={kolor} podpis={`${osoba.nazwa}\n${podsumowanie}`} onKlik={onWybierz} />
    </group>
  );
}

function Postac({ pozycja, kolor, podpis, onKlik }:
  { pozycja: [number, number, number]; kolor: string; podpis: string; onKlik?: () => void }) {
  const [najechana, ustawNajechana] = useState(false);
  return (
    <group position={pozycja}>
      <mesh position={[0, 0.9, 0]} castShadow
        onClick={(e) => { e.stopPropagation(); onKlik?.(); }}
        onPointerOver={() => ustawNajechana(true)} onPointerOut={() => ustawNajechana(false)}>
        <capsuleGeometry args={[0.35, 0.8, 8, 16]} />
        <meshStandardMaterial color={kolor} emissive={najechana ? kolor : "#000000"} emissiveIntensity={0.4} />
      </mesh>
      <Billboard position={[0, 2.3, 0]}>
        <Text fontSize={0.32} color="#e6edf7" anchorY="bottom" textAlign="center" maxWidth={4} outlineWidth={0.02} outlineColor="#0b1220">
          {podpis}
        </Text>
      </Billboard>
    </group>
  );
}
