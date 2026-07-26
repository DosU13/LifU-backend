import type { Element, ReceptacleRarity } from '../types'

/** Element colours, loosely following the Ayurvedic feel of each one. */
export const ELEMENT_COLOR: Record<Element, string> = {
  SPACE: '#6c5cf5',
  AIR: '#8fd3f4',
  FIRE: '#f2643d',
  WATER: '#3d9bf2',
  EARTH: '#7a9b52',
  HARMONY: '#f5e06c',
  GROWTH: '#5fbf7a',
  FORGE: '#c8622f',
  DUST: '#a89880',
  MOUNTAIN: '#8a8f9c',
  STEAM: '#c3d8e8',
  MIST: '#9fb6c8',
  OCEAN: '#2a7fa8',
  LIGHTNING: '#f0d040',
  SUN: '#f5a623',
  WIND: '#a8d8c0',
}

/** Treasures get richer as their contents do. */
export const RARITY_COLOR: Record<ReceptacleRarity, string> = {
  POUCH: '#8a7a62',
  SACK: '#a08a5c',
  CHEST: '#b8863b',
  SAFE: '#9aa4b0',
  VAULT: '#d4af37',
  SANCTUM: '#b06cf5',
}
