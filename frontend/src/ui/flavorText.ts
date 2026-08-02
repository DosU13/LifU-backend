import type { CollectableRarity, Element, ReceptacleRarity, Virtue } from '../types'

/**
 * A short mythical line for the inspect card — the tone borrowed from old
 * elemental-medicine folklore (tended seeds, remembered water, breath shared
 * between mouths) rather than the game's own mechanics, which the rest of the
 * card already states plainly.
 *
 * Built the same way the icon prompts are: one clause per element/virtue
 * crossed with one clause per rarity, so every one of the 96 + 60 combinations
 * reads as its own line without hand-authoring 156 sentences individually.
 */

const ELEMENT_LEGEND: Record<Element, string> = {
  SPACE: 'the void that is said to remember every word ever spoken into it',
  AIR: 'the breath once thought to carry a little of every life it touched',
  FIRE: 'the flame a village lit at a birth and never once let go out',
  WATER: 'the river-water a body is told it is only ever borrowing for a while',
  EARTH: 'the soil said to remember every promise ever buried beneath it',
  HARMONY: 'the old teaching that five separate elements were only forgetful of being one',
  GROWTH: 'the seed herbalists planted over grief, so the grief had somewhere to go',
  FORGE: 'the first hammer-blow a smith blesses, since the metal chooses its own shape',
  DUST: 'the road that is said to remember every foot that ever walked it',
  MOUNTAIN: 'the peak monks built their temple on, for a mountain forgets nothing at all',
  STEAM: 'the rising steam bathhouse keepers swore carried prayer higher than any voice could',
  MIST: 'the fog fishers would not speak of, only that it had seen them first',
  OCEAN: 'the tide line where sailors left offerings for a deep with its own accounts',
  LIGHTNING: 'the struck tree marking ground the sky itself is said to have chosen',
  SUN: 'the god a whole calendar was built around, and was told never once looked away',
  WIND: 'the wind a wanderer is named for, the one that passed through camp the night they were born',
}

const VIRTUE_LEGEND: Record<Virtue, string> = {
  NURTURING: 'the belief that anything tended long enough eventually tends you back',
  DETERMINATION: 'the old rule that a thing struck enough times stops being able to break',
  ADAPTABILITY: 'the teaching that water poured into any shape was never really trapped by it',
  PRESENCE: 'the stillness elders said a room remembers longer than it ever remembers noise',
  TRANSFORMATION: "the change healers refused to name, calling it neither an ending nor a start",
  REFLECTION: 'the still pool travelers were warned never to look into for too long',
  SERENITY: 'the deep water sailors swore had never once been troubled by a storm above it',
  INSPIRATION: 'the single struck spark every later fire is said to have borrowed from',
  VITALITY: 'the warmth a healer swore a body keeps lending out long after it should be spent',
  FREEDOM: 'the last knot every traveling story insists on leaving conspicuously untied',
}

const COLLECTABLE_TOUCH: Record<CollectableRarity, string> = {
  FRAGMENT: 'barely holding on to a memory of it',
  SHARD: 'sharp enough now to remember by itself',
  CRYSTAL: 'old enough that it would answer if you asked',
  ESSENCE: 'restless, as if it already knows the truth of it',
  SOUL: 'close to breaking its own long silence',
  CORE: 'past the point of forgetting anything at all',
}

const RECEPTACLE_TOUCH: Record<ReceptacleRarity, string> = {
  POUCH: 'barely worth a second glance, and it knows it',
  SACK: 'heavier in the hand than it looks',
  CHEST: 'locked for a reason nobody quite remembers now',
  SAFE: 'guarded the way you guard something that matters',
  VAULT: 'sealed the way you seal a promise, not a door',
  SANCTUM: "kept the way you'd keep something that was never really yours to open",
}

export function collectableFlavor(element: Element, rarity: CollectableRarity): string {
  return `Said to be ${ELEMENT_LEGEND[element]} — this one feels ${COLLECTABLE_TOUCH[rarity]}.`
}

export function receptacleFlavor(virtue: Virtue, rarity: ReceptacleRarity): string {
  return `Said to hold ${VIRTUE_LEGEND[virtue]} — this one is ${RECEPTACLE_TOUCH[rarity]}.`
}
