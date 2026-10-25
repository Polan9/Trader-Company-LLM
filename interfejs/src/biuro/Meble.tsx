import { useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { KOLORY, POKOJ, SALA, STOL, V3, X_POKOI } from "./uklad";

/** Podłogi trzech pokoi na wspólnej podstawie — „makieta” unosząca się w przestrzeni. */
export function Podlogi() {
  const szerokosc = SALA + POKOJ;
  return (
    <group>
      <mesh position={[POKOJ / 2, -0.35, 0]} receiveShadow>
        <boxGeometry args={[szerokosc + 0.6, 0.5, SALA + 0.6]} />
        <meshStandardMaterial color={KOLORY.podstawa} />
      </mesh>
      <mesh position={[0, -0.05, 0]} receiveShadow>
        <boxGeometry args={[SALA, 0.1, SALA]} />
        <meshStandardMaterial color={KOLORY.podlogaSali} />
      </mesh>
      <mesh position={[X_POKOI, -0.05, -POKOJ / 2]} receiveShadow>
        <boxGeometry args={[POKOJ, 0.1, POKOJ]} />
        <meshStandardMaterial color={KOLORY.podlogaHeadTradera} />
      </mesh>
      <mesh position={[X_POKOI, -0.05, POKOJ / 2]} receiveShadow>
        <boxGeometry args={[POKOJ, 0.1, POKOJ]} />
        <meshStandardMaterial color={KOLORY.podlogaPersonelu} />
      </mesh>
      {/* dywan pod stołem */}
      <mesh position={[0, 0.005, 0]} rotation={[-Math.PI / 2, 0, 0]} scale={[STOL.polosX + 2.6, STOL.polosZ + 2.4, 1]} receiveShadow>
        <circleGeometry args={[1, 64]} />
        <meshStandardMaterial color="#4a3b5c" />
      </mesh>
    </group>
  );
}

/** Owalny stół; `swiatlo` — kolor poświaty (wynik głosowania w trakcie odtwarzania). */
export function StolOwalny({ swiatlo }: { swiatlo: string | null }) {
  const blat = useRef<THREE.MeshStandardMaterial>(null);
  useFrame(({ clock }) => {
    if (!blat.current) return;
    blat.current.emissive.set(swiatlo ?? "#000000");
    blat.current.emissiveIntensity = swiatlo ? 0.25 + Math.sin(clock.elapsedTime * 4) * 0.1 : 0;
  });
  return (
    <group>
      <mesh position={[0, STOL.wysokosc, 0]} scale={[STOL.polosX, 1, STOL.polosZ]} castShadow receiveShadow>
        <cylinderGeometry args={[1, 1, 0.1, 64]} />
        <meshStandardMaterial ref={blat} color="#7a5233" roughness={0.6} />
      </mesh>
      {[-1.6, 1.6].map((x) => (
        <mesh key={x} position={[x, STOL.wysokosc / 2, 0]} castShadow>
          <cylinderGeometry args={[0.25, 0.4, STOL.wysokosc, 16]} />
          <meshStandardMaterial color="#4a3423" />
        </mesh>
      ))}
    </group>
  );
}

export function Krzeslo({ pozycja, obrot, kolor = "#2f3b52" }: { pozycja: V3; obrot: number; kolor?: string }) {
  return (
    <group position={pozycja} rotation={[0, obrot, 0]}>
      <mesh position={[0, 0.45, 0]} castShadow>
        <boxGeometry args={[0.6, 0.1, 0.6]} />
        <meshStandardMaterial color={kolor} />
      </mesh>
      <mesh position={[0, 0.85, -0.28]} castShadow>
        <boxGeometry args={[0.6, 0.8, 0.08]} />
        <meshStandardMaterial color={kolor} />
      </mesh>
      <mesh position={[0, 0.22, 0]}>
        <cylinderGeometry args={[0.05, 0.05, 0.44, 8]} />
        <meshStandardMaterial color="#1c2433" />
      </mesh>
    </group>
  );
}

/** Biurko z monitorem; `ekran` — kolor ekranu (świeci, gdy stanowisko jest aktywne). */
export function Biurko({ pozycja, obrot = 0, ekran = "#1f3550", aktywne = false }:
  { pozycja: V3; obrot?: number; ekran?: string; aktywne?: boolean }) {
  return (
    <group position={pozycja} rotation={[0, obrot, 0]}>
      <mesh position={[0, 0.74, 0]} castShadow receiveShadow>
        <boxGeometry args={[1.6, 0.06, 0.8]} />
        <meshStandardMaterial color="#8a6a4a" />
      </mesh>
      {[[-0.72, -0.32], [0.72, -0.32], [-0.72, 0.32], [0.72, 0.32]].map(([x, z]) => (
        <mesh key={`${x}${z}`} position={[x, 0.37, z]}>
          <boxGeometry args={[0.06, 0.74, 0.06]} />
          <meshStandardMaterial color="#3a2c20" />
        </mesh>
      ))}
      {/* monitor po stronie +Z biurka; osoba siedzi po stronie −Z (obrót biurka ustawia kierunek) */}
      <mesh position={[0, 1.12, 0.25]} castShadow>
        <boxGeometry args={[0.9, 0.55, 0.05]} />
        <meshStandardMaterial color="#111827" emissive={aktywne ? ekran : "#0b1220"} emissiveIntensity={aktywne ? 0.9 : 0.4} />
      </mesh>
      <mesh position={[0, 0.82, 0.25]}>
        <boxGeometry args={[0.08, 0.12, 0.08]} />
        <meshStandardMaterial color="#111827" />
      </mesh>
    </group>
  );
}

export function Roslina({ pozycja }: { pozycja: V3 }) {
  return (
    <group position={pozycja}>
      <mesh position={[0, 0.25, 0]} castShadow>
        <cylinderGeometry args={[0.25, 0.2, 0.5, 12]} />
        <meshStandardMaterial color="#8b5e3c" />
      </mesh>
      <mesh position={[0, 0.9, 0]} castShadow>
        <sphereGeometry args={[0.5, 16, 16]} />
        <meshStandardMaterial color="#3f7d4e" />
      </mesh>
    </group>
  );
}
