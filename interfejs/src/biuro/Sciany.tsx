import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import {
  GRUBOSC_SCIANY, KOLORY, POKOJ, SALA, SZEROKOSC_DRZWI, V3, WYSOKOSC_SCIANKI, WYSOKOSC_SCIANY, X_POKOI,
} from "./uklad";

interface DefinicjaSciany {
  srodek: V3; // środek podstawy ściany
  dlugosc: number;
  wzdluzX: boolean; // true: ściana biegnie wzdłuż osi X, false: wzdłuż Z
  normalna: [number, number] | null; // kierunek „na zewnątrz” — null: ściana wewnętrzna, nie znika
  wysokosc: number;
}

/** Odcinki ściany z przerwami na drzwi (pozycje środków drzwi wzdłuż ściany). */
function zDrzwiami(od: number, doPozycji: number, drzwi: number[]): [number, number][] {
  const odcinki: [number, number][] = [];
  let start = od;
  for (const d of [...drzwi].sort((a, b) => a - b)) {
    odcinki.push([start, d - SZEROKOSC_DRZWI / 2]);
    start = d + SZEROKOSC_DRZWI / 2;
  }
  odcinki.push([start, doPozycji]);
  return odcinki.filter(([a, b]) => b - a > 0.05);
}

function scianyBiura(): DefinicjaSciany[] {
  const h = SALA / 2;
  const prawaKrawedz = SALA / 2 + POKOJ;
  const sciany: DefinicjaSciany[] = [
    // Główny pokój: północ, zachód, południe
    { srodek: [0, 0, -h], dlugosc: SALA, wzdluzX: true, normalna: [0, -1], wysokosc: WYSOKOSC_SCIANY },
    { srodek: [-h, 0, 0], dlugosc: SALA, wzdluzX: false, normalna: [-1, 0], wysokosc: WYSOKOSC_SCIANY },
    { srodek: [0, 0, h], dlugosc: SALA, wzdluzX: true, normalna: [0, 1], wysokosc: WYSOKOSC_SCIANY },
    // Pokoje po prawej: północ, wschód, południe
    { srodek: [X_POKOI, 0, -h], dlugosc: POKOJ, wzdluzX: true, normalna: [0, -1], wysokosc: WYSOKOSC_SCIANY },
    { srodek: [prawaKrawedz, 0, 0], dlugosc: SALA, wzdluzX: false, normalna: [1, 0], wysokosc: WYSOKOSC_SCIANY },
    { srodek: [X_POKOI, 0, h], dlugosc: POKOJ, wzdluzX: true, normalna: [0, 1], wysokosc: WYSOKOSC_SCIANY },
  ];
  // Ściana między salą a pokojami po prawej — drzwi do gabinetu Head Tradera i do pokoju personelu
  for (const [a, b] of zDrzwiami(-h, h, [-POKOJ / 2, POKOJ / 2])) {
    sciany.push({ srodek: [h, 0, (a + b) / 2], dlugosc: b - a, wzdluzX: false, normalna: [1, 0], wysokosc: WYSOKOSC_SCIANY });
  }
  // Niska ścianka między gabinetem Head Tradera a pokojem personelu, z przejściem
  for (const [a, b] of zDrzwiami(h, prawaKrawedz, [X_POKOI])) {
    sciany.push({ srodek: [(a + b) / 2, 0, 0], dlugosc: b - a, wzdluzX: true, normalna: null, wysokosc: WYSOKOSC_SCIANKI });
  }
  return sciany;
}

/** Ściana, która staje się prawie przezroczysta, gdy kamera patrzy na nią od zewnątrz — widok jak w makiecie. */
function ScianaZanikajaca({ sciana }: { sciana: DefinicjaSciany }) {
  const material = useRef<THREE.MeshStandardMaterial>(null);
  const [x, , z] = sciana.srodek;

  useFrame(({ camera }) => {
    if (!material.current || !sciana.normalna) return;
    const [nx, nz] = sciana.normalna;
    const zewnatrz = (camera.position.x - x) * nx + (camera.position.z - z) * nz > 0;
    const cel = zewnatrz ? 0.08 : 1;
    material.current.opacity += (cel - material.current.opacity) * 0.15; // płynne przejście
    material.current.depthWrite = material.current.opacity > 0.5;
  });

  const rozmiar: V3 = sciana.wzdluzX
    ? [sciana.dlugosc, sciana.wysokosc, GRUBOSC_SCIANY]
    : [GRUBOSC_SCIANY, sciana.wysokosc, sciana.dlugosc];
  return (
    <mesh position={[x, sciana.wysokosc / 2, z]} castShadow receiveShadow>
      <boxGeometry args={rozmiar} />
      <meshStandardMaterial ref={material} color={KOLORY.sciana} transparent opacity={sciana.normalna ? 1 : 0.85} />
    </mesh>
  );
}

export default function Sciany() {
  return (
    <group>
      {scianyBiura().map((s, i) => <ScianaZanikajaca key={i} sciana={s} />)}
    </group>
  );
}
