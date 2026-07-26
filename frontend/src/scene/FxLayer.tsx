import { useFrame } from '@react-three/fiber'
import { useEffect, useRef, useState } from 'react'
import type { Group } from 'three'

import { useGameStore } from '../state/store'
import type { FxEvent } from '../state/store'
import { RARITY_COLOR } from './colors'

const BURST_SECONDS = 0.32
const DROP_SECONDS = 1.1
const SLOT_SPACING = 2.6

/**
 * Replays the harmony build-up: one pulse for the guaranteed five, then one
 * more for each extra the server actually rolled. The count is never invented
 * here — `bursts` comes straight from the API response.
 */
function HarmonyBurst({ event, onDone }: { event: FxEvent & { kind: 'harmony' }; onDone: () => void }) {
  const group = useRef<Group>(null)
  const [index, setIndex] = useState(0)
  const elapsed = useRef(0)

  useFrame((_, delta) => {
    elapsed.current += delta
    const progress = elapsed.current / BURST_SECONDS

    if (group.current) {
      const scale = 0.4 + progress * 1.4
      group.current.scale.set(scale, scale, scale)
      group.current.rotation.z += delta * 2
    }

    if (progress >= 1) {
      elapsed.current = 0
      const next = index + 1
      if (next >= event.bursts) onDone()
      else setIndex(next)
    }
  })

  // Later pulses sit higher, so a long build-up visibly climbs.
  const opacity = 0.85
  return (
    <group ref={group} position={[0, 0.4 + index * 0.12, 1]}>
      <mesh>
        <ringGeometry args={[0.5, 0.62, 32]} />
        <meshBasicMaterial color="#f5e06c" transparent opacity={opacity} />
      </mesh>
    </group>
  )
}

/** A dropped receptacle rising out of its treasure. */
function DropReveal({ event, onDone }: { event: FxEvent & { kind: 'drop' }; onDone: () => void }) {
  const group = useRef<Group>(null)
  const elapsed = useRef(0)
  const treasureCount = useGameStore((s) => s.treasures.length)

  useFrame((_, delta) => {
    elapsed.current += delta
    const progress = Math.min(elapsed.current / DROP_SECONDS, 1)

    if (group.current) {
      group.current.position.y = 0.6 + progress * 1.6
      group.current.rotation.y += delta * 3
      const fade = 1 - progress
      group.current.scale.setScalar(0.4 + fade * 0.5)
    }

    if (progress >= 1) onDone()
  })

  const offset = ((Math.max(treasureCount, 1) - 1) * SLOT_SPACING) / 2
  const x = event.slot * SLOT_SPACING - offset

  return (
    <group ref={group} position={[x, 0.6, 1]}>
      <mesh>
        <octahedronGeometry args={[0.45]} />
        <meshStandardMaterial
          color={RARITY_COLOR[event.rarity]}
          emissive={RARITY_COLOR[event.rarity]}
          emissiveIntensity={0.6}
        />
      </mesh>
    </group>
  )
}

/** A soft flash when a receptacle is opened. */
function OpenFlash({ onDone }: { onDone: () => void }) {
  const group = useRef<Group>(null)
  const elapsed = useRef(0)

  useFrame((_, delta) => {
    elapsed.current += delta
    const progress = Math.min(elapsed.current / 0.7, 1)
    if (group.current) group.current.scale.setScalar(0.3 + progress * 3)
    if (progress >= 1) onDone()
  })

  return (
    <group ref={group} position={[0, 0.4, 1]}>
      <mesh>
        <ringGeometry args={[0.4, 0.5, 32]} />
        <meshBasicMaterial color="#ffd98a" transparent opacity={0.7} />
      </mesh>
    </group>
  )
}

export function FxLayer() {
  const fx = useGameStore((s) => s.fx)
  const consumeFx = useGameStore((s) => s.consumeFx)

  // Play one effect at a time so a burst of actions reads as a sequence.
  const current = fx[0]

  // Safety net: never let a stuck effect block the queue forever.
  useEffect(() => {
    if (!current) return
    const timer = setTimeout(() => consumeFx(current.id), 8000)
    return () => clearTimeout(timer)
  }, [current, consumeFx])

  if (!current) return null

  const done = () => consumeFx(current.id)

  if (current.kind === 'harmony') {
    return <HarmonyBurst key={current.id} event={current} onDone={done} />
  }
  if (current.kind === 'drop') {
    return <DropReveal key={current.id} event={current} onDone={done} />
  }
  return <OpenFlash key={current.id} onDone={done} />
}
