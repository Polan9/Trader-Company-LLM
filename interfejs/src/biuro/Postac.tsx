import { ReactNode, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import { Billboard, Html, Text } from "@react-three/drei";
import * as THREE from "three";
import { V3 } from "./uklad";

export interface WlasciwosciPostaci {
  pozycja: V3;
  obrot?: number;
  kolorKoszuli: string;
  kolorStatusu: string | null; // pierścień pod postacią: wynik głosu (null = brak)
  siedzi?: boolean;
  aktywna?: boolean; // „mówi” — podskakuje i świeci (w trakcie odtwarzania)
  przygaszona?: boolean; // nieaktywny trader
  podpis: string;
  dymek?: ReactNode;
  onKlik?: () => void;
}

/** Postać z prostych brył: tułów, głowa, ręce. Przy biurku/stole siedzi; aktywna lekko podskakuje. */
export default function Postac({
  pozycja, obrot = 0, kolorKoszuli, kolorStatusu, siedzi = true, aktywna = false, przygaszona = false,
  podpis, dymek, onKlik,
}: WlasciwosciPostaci) {
  const cialo = useRef<THREE.Group>(null);
  const pierscien = useRef<THREE.MeshStandardMaterial>(null);
  const [najechana, ustawNajechana] = useState(false);
  const faza = useRef(Math.random() * Math.PI * 2); // każda postać „oddycha” w innym rytmie

  useFrame(({ clock }, delta) => {
    if (!cialo.current) return;
    const t = clock.elapsedTime + faza.current;
    const podskok = aktywna ? Math.abs(Math.sin(t * 6)) * 0.12 : Math.sin(t * 1.5) * 0.015;
    cialo.current.position.y += (podskok - cialo.current.position.y) * Math.min(1, delta * 12);
    if (pierscien.current) pierscien.current.emissiveIntensity = aktywna ? 1.2 + Math.sin(t * 8) * 0.4 : 0.5;
  });

  const y = siedzi ? 0.5 : 0;
  const skora = przygaszona ? "#6b7280" : "#e8c4a0";
  const koszula = przygaszona ? "#4a5568" : kolorKoszuli;
  const podswietlenie = najechana || aktywna ? 0.35 : 0;

  return (
    <group position={pozycja} rotation={[0, obrot, 0]}>
      {kolorStatusu && (
        <mesh position={[0, 0.02, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[0.45, 0.6, 32]} />
          <meshStandardMaterial ref={pierscien} color={kolorStatusu} emissive={kolorStatusu} emissiveIntensity={0.5} />
        </mesh>
      )}
      <group ref={cialo}>
        <group position={[0, y, 0]}
          onClick={(e) => { e.stopPropagation(); onKlik?.(); }}
          onPointerOver={(e) => { e.stopPropagation(); ustawNajechana(true); document.body.style.cursor = "pointer"; }}
          onPointerOut={() => { ustawNajechana(false); document.body.style.cursor = "auto"; }}>
          {/* tułów */}
          <mesh position={[0, 0.45, 0]} castShadow>
            <capsuleGeometry args={[0.24, 0.45, 6, 12]} />
            <meshStandardMaterial color={koszula} emissive={koszula} emissiveIntensity={podswietlenie} />
          </mesh>
          {/* głowa */}
          <mesh position={[0, 1.05, 0]} castShadow>
            <sphereGeometry args={[0.2, 20, 20]} />
            <meshStandardMaterial color={skora} />
          </mesh>
          {/* oczy — postać patrzy w stronę +Z */}
          {[-0.07, 0.07].map((x) => (
            <mesh key={x} position={[x, 1.08, 0.18]}>
              <sphereGeometry args={[0.025, 8, 8]} />
              <meshStandardMaterial color="#1a1a1a" />
            </mesh>
          ))}
          {/* ręce wyciągnięte do przodu (na stół / biurko) */}
          {[-0.3, 0.3].map((x) => (
            <mesh key={x} position={[x, 0.5, 0.18]} rotation={[Math.PI / 2.6, 0, 0]} castShadow>
              <capsuleGeometry args={[0.07, 0.35, 4, 8]} />
              <meshStandardMaterial color={koszula} />
            </mesh>
          ))}
          {!siedzi && [-0.12, 0.12].map((x) => (
            <mesh key={x} position={[x, -0.25, 0]} castShadow>
              <capsuleGeometry args={[0.08, 0.45, 4, 8]} />
              <meshStandardMaterial color="#2b3445" />
            </mesh>
          ))}
        </group>
      </group>
      <Billboard position={[0, y + 1.55, 0]}>
        <Text fontSize={0.24} color={przygaszona ? "#8b97ab" : "#f1f5fb"} anchorY="bottom" textAlign="center"
          maxWidth={3.2} outlineWidth={0.025} outlineColor="#0b1220">
          {podpis}
        </Text>
      </Billboard>
      {dymek && (
        <Html position={[0, y + 2.35, 0]} center distanceFactor={14} zIndexRange={[20, 0]}>
          <div className={aktywna ? "dymek aktywny" : "dymek"}>{dymek}</div>
        </Html>
      )}
    </group>
  );
}
