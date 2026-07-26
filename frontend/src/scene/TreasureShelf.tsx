import { useFrame } from '@react-three/fiber'
import { useRef, useState } from 'react'
import type { Group, Mesh } from 'three'

import { useGameStore } from '../state/store'
import type { Treasure } from '../types'
import { RARITY_COLOR } from './colors'

const SLOT_SPACING = 2.6
// An orthographic camera pointed straight at a box shows one flat face, so the
// whole shelf is turned a little: enough to see the top and one side, which is
// what makes the geometry read as solid rather than as a coloured rectangle.
const VIEW_YAW = 0.42
const VIEW_PITCH = 0.3

/** The rarest thing a treasure holds — what the chest colour advertises. */
function headlineRarity(treasure: Treasure) {
  const order = ['POUCH', 'SACK', 'CHEST', 'SAFE', 'VAULT', 'SANCTUM'] as const
  let best: (typeof order)[number] = 'CHEST'
  for (const item of treasure.contents) {
    if (order.indexOf(item.rarity) > order.indexOf(best)) best = item.rarity
  }
  return best
}

interface ChestProps {
  treasure: Treasure
  x: number
  selected: boolean
  onSelect: () => void
}

function Chest({ treasure, x, selected, onSelect }: ChestProps) {
  const group = useRef<Group>(null)
  const lid = useRef<Mesh>(null)
  const [hovered, setHovered] = useState(false)

  // A gentle bob, a little livelier for the selected chest. useFrame runs on
  // every rendered frame; `delta` keeps motion frame-rate independent.
  useFrame((state) => {
    if (!group.current) return
    const t = state.clock.elapsedTime + treasure.slot
    const lift = selected ? 0.18 : 0.06
    group.current.position.y = Math.sin(t * 1.4) * lift
    const targetScale = selected ? 1.12 : hovered ? 1.05 : 1
    group.current.scale.lerp({ x: targetScale, y: targetScale, z: targetScale } as never, 0.15)
    // Drift the yaw a little so the lit side and top stay readable as it moves.
    group.current.rotation.y = VIEW_YAW + Math.sin(t * 0.5) * 0.08
    if (lid.current) lid.current.rotation.x = selected ? -0.5 : -0.12
  })

  const color = RARITY_COLOR[headlineRarity(treasure)]

  return (
    <group
      ref={group}
      position={[x, 0, 0]}
      onClick={(event) => {
        event.stopPropagation()
        onSelect()
      }}
      onPointerOver={(event) => {
        event.stopPropagation()
        setHovered(true)
        document.body.style.cursor = 'pointer'
      }}
      onPointerOut={() => {
        setHovered(false)
        document.body.style.cursor = 'auto'
      }}
    >
      {/* body */}
      <mesh position={[0, -0.15, 0]}>
        <boxGeometry args={[1.6, 1, 1.1]} />
        <meshStandardMaterial color={color} roughness={0.55} metalness={0.25} />
      </mesh>
      {/* lid, hinged at the back so it tips open when selected */}
      <mesh ref={lid} position={[0, 0.38, -0.55]}>
        <boxGeometry args={[1.62, 0.28, 1.12]} />
        <meshStandardMaterial color={color} roughness={0.4} metalness={0.35} />
      </mesh>
      {/* a warm glow inside the open lid */}
      {selected && (
        <mesh position={[0, 0.3, 0]}>
          <boxGeometry args={[1.3, 0.1, 0.85]} />
          <meshBasicMaterial color="#ffd98a" />
        </mesh>
      )}
    </group>
  )
}

export function TreasureShelf() {
  const treasures = useGameStore((s) => s.treasures)
  const selectedId = useGameStore((s) => s.selectedTreasureId)
  const selectTreasure = useGameStore((s) => s.selectTreasure)

  const offset = ((treasures.length - 1) * SLOT_SPACING) / 2

  return (
    <group position={[0, 0.6, 0]} rotation={[VIEW_PITCH, 0, 0]}>
      {treasures.map((treasure, index) => (
        <Chest
          key={treasure.id}
          treasure={treasure}
          x={index * SLOT_SPACING - offset}
          selected={treasure.id === selectedId}
          onSelect={() => selectTreasure(treasure.id === selectedId ? null : treasure.id)}
        />
      ))}
    </group>
  )
}
