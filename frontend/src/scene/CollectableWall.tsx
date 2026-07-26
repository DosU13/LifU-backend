import { useFrame } from '@react-three/fiber'
import { useMemo, useRef } from 'react'
import type { Group } from 'three'

import { useGameStore } from '../state/store'
import { COLLECTABLE_RARITIES, ELEMENTS, stockKey } from '../types'
import { ELEMENT_COLOR } from './colors'

const COLUMNS = 8
const SPACING = 0.42
// Higher rarities are bigger and spin faster, so a Core reads as special at a glance.
const SIZE_BY_RARITY = [0.16, 0.2, 0.24, 0.28, 0.32, 0.38]

interface Held {
  key: string
  color: string
  rarityIndex: number
  count: number
}

function Gem({ held, x, y }: { held: Held; x: number; y: number }) {
  const group = useRef<Group>(null)

  useFrame((_, delta) => {
    if (!group.current) return
    group.current.rotation.y += delta * (0.3 + held.rarityIndex * 0.15)
  })

  const size = SIZE_BY_RARITY[held.rarityIndex] ?? 0.16

  return (
    <group ref={group} position={[x, y, 0]}>
      {/* An octahedron reads as a gem from any angle and costs almost nothing to draw. */}
      <mesh>
        <octahedronGeometry args={[size]} />
        <meshStandardMaterial
          color={held.color}
          roughness={0.25}
          metalness={0.5}
          emissive={held.color}
          emissiveIntensity={0.15 + held.rarityIndex * 0.08}
        />
      </mesh>
    </group>
  )
}

export function CollectableWall() {
  const stocks = useGameStore((s) => s.stocks)

  const held = useMemo<Held[]>(() => {
    const result: Held[] = []
    for (const element of ELEMENTS) {
      COLLECTABLE_RARITIES.forEach((rarity, rarityIndex) => {
        const count = stocks[stockKey(element, rarity)] ?? 0
        if (count > 0) {
          result.push({
            key: stockKey(element, rarity),
            color: ELEMENT_COLOR[element],
            rarityIndex,
            count,
          })
        }
      })
    }
    return result
  }, [stocks])

  const offset = ((COLUMNS - 1) * SPACING) / 2

  return (
    <group position={[0, -1.5, 0]}>
      {held.map((item, index) => (
        <Gem
          key={item.key}
          held={item}
          x={(index % COLUMNS) * SPACING - offset}
          y={-Math.floor(index / COLUMNS) * SPACING}
        />
      ))}
    </group>
  )
}
