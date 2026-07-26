import { Canvas } from '@react-three/fiber'

import { CollectableWall } from './CollectableWall'
import { FxLayer } from './FxLayer'
import { TreasureShelf } from './TreasureShelf'

/**
 * The 3D stage. Deliberately 2.5D: an orthographic camera looking straight at
 * the XY plane, so everything reads like a flat board while still being real
 * geometry with real lighting — the simplest way in to three.js.
 *
 * Nothing in here decides game rules. Scene components read the store and
 * animate what already happened.
 */
export function SceneCanvas() {
  return (
    <div className="scene">
      <Canvas
        orthographic
        camera={{ position: [0, 0, 10], zoom: 88 }}
        // Cap the pixel ratio: retina screens otherwise render 4x the pixels
        // for no visible gain here.
        dpr={[1, 1.75]}
      >
        <ambientLight intensity={0.75} />
        <directionalLight position={[3, 5, 6]} intensity={1.1} />
        <directionalLight position={[-4, -2, 3]} intensity={0.35} color="#8fa8ff" />

        <TreasureShelf />
        <CollectableWall />
        <FxLayer />
      </Canvas>
    </div>
  )
}
