import { useEffect, useRef } from 'react';
import { useGLTF } from '@react-three/drei';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { useViewerStore } from '@/stores/useViewerStore';

interface TryOnModelProps {
  url: string;
}

/**
 * Loads a .glb mesh (from TRELLIS pipeline output) and upgrades
 * materials to MeshPhysicalMaterial for PBR realism.
 */
export default function TryOnModel({ url }: TryOnModelProps) {
  const { scene } = useGLTF(url);
  const groupRef = useRef<THREE.Group>(null);
  const setModelLoading = useViewerStore((s) => s.setModelLoading);
  const setModelError = useViewerStore((s) => s.setModelError);

  useEffect(() => {
    setModelLoading(true);

    try {
      // Center and scale the model
      const box = new THREE.Box3().setFromObject(scene);
      const center = box.getCenter(new THREE.Vector3());
      const size = box.getSize(new THREE.Vector3());
      const maxDim = Math.max(size.x, size.y, size.z);
      const scale = 2 / maxDim; // Normalize to ~2 units height

      scene.position.set(-center.x * scale, -box.min.y * scale, -center.z * scale);
      scene.scale.setScalar(scale);

      // Upgrade materials to MeshPhysicalMaterial for PBR
      scene.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.castShadow = true;
          child.receiveShadow = true;

          if (child.material) {
            const oldMat = child.material as THREE.MeshStandardMaterial;
            const physicalMat = new THREE.MeshPhysicalMaterial({
              map: oldMat.map,
              normalMap: oldMat.normalMap,
              roughnessMap: oldMat.roughnessMap,
              metalnessMap: oldMat.metalnessMap,
              aoMap: oldMat.aoMap,
              emissiveMap: oldMat.emissiveMap,
              emissive: oldMat.emissive,
              color: oldMat.color,
              roughness: oldMat.roughness ?? 0.7,
              metalness: oldMat.metalness ?? 0.0,
              clearcoat: 0.05,
              clearcoatRoughness: 0.3,
              envMapIntensity: 1.2,
              side: THREE.DoubleSide,
            });
            child.material = physicalMat;
          }
        }
      });

      setModelLoading(false);
      setModelError(null);
    } catch (err) {
      console.error('[TryOnModel] Error processing model:', err);
      setModelLoading(false);
      setModelError(err instanceof Error ? err.message : 'Failed to load model');
    }
  }, [scene, setModelLoading, setModelError]);

  // Subtle idle breathing animation
  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.02;
    }
  });

  return (
    <group ref={groupRef}>
      <primitive object={scene} />
    </group>
  );
}

// Pre-warm GLTF loader cache
useGLTF.preload('/models/placeholder.glb');
