import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import * as THREE from "three";
import { V3 } from "./uklad";

/** Przepływ danych między stanowiskami: łuk nad makietą i kulka „wiadomości” biegnąca po nim. */
export default function Przeplyw({ od, do: cel, kolor = "#f5c542" }: { od: V3; do: V3; kolor?: string }) {
  const kulka = useRef<THREE.Mesh>(null);
  const krzywa = useMemo(() => {
    const a = new THREE.Vector3(od[0], 1.6, od[2]);
    const b = new THREE.Vector3(cel[0], 1.6, cel[2]);
    const srodek = a.clone().lerp(b, 0.5).setY(3.5 + a.distanceTo(b) * 0.15);
    return new THREE.QuadraticBezierCurve3(a, srodek, b);
  }, [od, cel]);
  const punkty = useMemo(() => krzywa.getPoints(40), [krzywa]);

  useFrame(({ clock }) => {
    if (kulka.current) kulka.current.position.copy(krzywa.getPoint((clock.elapsedTime * 0.8) % 1));
  });

  return (
    <group>
      <Line points={punkty} color={kolor} lineWidth={2} dashed dashSize={0.3} gapSize={0.2} transparent opacity={0.7} />
      <mesh ref={kulka}>
        <sphereGeometry args={[0.15, 16, 16]} />
        <meshStandardMaterial color={kolor} emissive={kolor} emissiveIntensity={1.5} />
      </mesh>
    </group>
  );
}
