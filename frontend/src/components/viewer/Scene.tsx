import { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import {
  OrbitControls,
  Environment,
  ContactShadows,
  Grid,
  PerspectiveCamera,
} from '@react-three/drei';
import { EffectComposer, SMAA } from '@react-three/postprocessing';
import { useViewerStore } from '@/stores/useViewerStore';
import TryOnModel from './TryOnModel';

interface SceneProps {
  meshUrl: string;
}

function SceneContent({ meshUrl }: SceneProps) {
  const { camera, showGrid, environmentPreset, quality } =
    useViewerStore();

  return (
    <>
      {/* Camera */}
      <PerspectiveCamera
        makeDefault
        position={camera.position}
        fov={camera.fov}
      />

      {/* Controls */}
      <OrbitControls
        target={camera.target}
        autoRotate={camera.autoRotate}
        autoRotateSpeed={camera.autoRotateSpeed}
        enablePan={true}
        enableZoom={true}
        enableDamping={true}
        dampingFactor={0.05}
        minDistance={1}
        maxDistance={8}
        minPolarAngle={Math.PI * 0.1}
        maxPolarAngle={Math.PI * 0.85}
      />

      {/* Environment Lighting */}
      <Environment preset={environmentPreset as any} background={false} />
      <ambientLight intensity={0.3} />
      <directionalLight
        position={[5, 5, 5]}
        intensity={0.8}
        castShadow
        shadow-mapSize={[1024, 1024]}
      />
      <directionalLight position={[-3, 3, -3]} intensity={0.3} />

      {/* Model */}
      <Suspense fallback={null}>
        <TryOnModel url={meshUrl} />
      </Suspense>

      {/* Ground */}
      <ContactShadows
        position={[0, -0.01, 0]}
        opacity={0.4}
        scale={10}
        blur={2}
        far={4}
      />

      {showGrid && (
        <Grid
          position={[0, -0.01, 0]}
          args={[10, 10]}
          cellSize={0.5}
          cellThickness={0.5}
          cellColor="#333"
          sectionSize={2}
          sectionThickness={1}
          sectionColor="#555"
          fadeDistance={10}
          fadeStrength={1}
          infiniteGrid
        />
      )}

      {/* Post Processing */}
      {quality !== 'low' && (
        <EffectComposer>
          <SMAA />
        </EffectComposer>
      )}
    </>
  );
}

export default function Scene({ meshUrl }: SceneProps) {
  return (
    <div className="canvas-container w-full h-full min-h-[500px] rounded-2xl overflow-hidden">
      <Canvas
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: 'high-performance',
          preserveDrawingBuffer: true,
        }}
        shadows
        dpr={[1, 2]}
        onCreated={({ gl }) => {
          gl.toneMapping = 4; // ACESFilmicToneMapping
          gl.toneMappingExposure = 1.0;
        }}
      >
        <SceneContent meshUrl={meshUrl} />
      </Canvas>
    </div>
  );
}
