"""Prompt assembly for the 156 game icons.

96 collectables (16 elements x 6 rarities) + 60 receptacles (10 virtues x 6
rarities), one prompt each. See docs/ICON_PROMPTS.md for the art direction and
the reasoning behind the escalation ladder.

The enum sets are imported from backend/core rather than restated, so adding a
sixteenth-and-a-half element can never leave this tool generating a stale set.
core/ is pure Python with no dependencies, so importing it costs nothing.
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from core.enums import CollectableRarity, Element, ReceptacleRarity, Virtue  # noqa: E402
from core.mappings import VIRTUE_ELEMENT  # noqa: E402

# --- style block: identical in all 156 prompts ---
# This is the only thing keeping 156 independently generated images in one
# visual world. Do not reword it per subject.
STYLE = (
    "Game inventory icon, painted 3D-render style with a clean readable silhouette. "
    "Semi-realistic fantasy materials, stone and metal and glass and contained energy. "
    "Single light source from the upper left, soft ambient bounce, subtle rim light. "
    "Rich saturated colour, deep contrast, no outlines, no cel shading. "
    "One single object, centred, three-quarter view, floating with no ground plane "
    "and no cast shadow."
)

OUTPUT = (
    "The background is a completely flat solid magenta field, uniform, with no gradient "
    "and no texture and no shadow. Square image. "
    "There is no text anywhere in the image, no letters, no numbers, no words, "
    "no watermark, no signature, no border, no frame, no user interface."
)

# --- the escalation ladder ---
# Each block is self-contained and absolute: these are generated in separate
# passes, so "bigger than the last one" would be meaningless. Escalation rides
# on silhouette, emitted light, and implied motion -- never on fine detail,
# which vanishes when these are drawn at 96px.

COLLECTABLE_LADDER: dict[CollectableRarity, str] = {
    CollectableRarity.FRAGMENT: (
        "The object is a FRAGMENT: a single small chipped piece broken off something "
        "larger. Rough matte unpolished mineral with a dusty surface and sharp fractured "
        "edges. The colour is present but muted and dull, as if seen through dirty stone. "
        "It emits no light whatsoever and has no glow. It looks like a worthless scrap "
        "found on the ground. It is small and occupies only the centre of the frame."
    ),
    CollectableRarity.SHARD: (
        "The object is a SHARD: a single cleanly cleaved splinter with two or three flat "
        "fracture planes. Semi-translucent along its thin edges with a faint sheen "
        "catching the light. The colour is now clearly visible in its interior. It is "
        "still inert: it reflects light but produces none of its own. It occupies a "
        "little under half the frame."
    ),
    CollectableRarity.CRYSTAL: (
        "The object is a CRYSTAL: a deliberately cut faceted geometric gemstone, "
        "symmetrical and precise rather than broken. A glassy translucent body with a "
        "soft internal glow beginning at its centre. A thin band of polished metal wraps "
        "its base, the first sign of craftsmanship. Its faint light bleeds onto the metal. "
        "It occupies about half the frame."
    ),
    CollectableRarity.ESSENCE: (
        "The object is an ESSENCE: a refined teardrop of clear crystal holding the "
        "element inside it as a visibly liquid, swirling, living substance. It is held in "
        "an ornate engraved metal setting. It emits real light, casting coloured "
        "illumination onto its own frame, and a few slow glowing motes drift free around "
        "it. It occupies about two thirds of the frame."
    ),
    CollectableRarity.SOUL: (
        "The object is a SOUL: its containment is straining and about to fail. A brilliant "
        "nucleus pulses at the centre, wrapped in a cracked broken shell whose pieces have "
        "come apart and float in slow orbit around it, held in place by force rather than "
        "structure. Hard beams of light escape through the cracks and a luminous aura "
        "spills past the object's edge and lights the surrounding air. It fills most of "
        "the frame."
    ),
    CollectableRarity.CORE: (
        "The object is a CORE: a contained star. Perfect radial symmetry around a "
        "blindingly bright origin point at its centre, ringed by concentric floating "
        "structures of dark metal inscribed with glowing sacred geometry. Several orbits "
        "of debris circle it at different angles. Space visibly bends and distorts around "
        "it, the surrounding air is thick with charged drifting particulate, and its light "
        "floods the entire image edge to edge. It reads as an artifact older than the "
        "world. It is enormous and fills the whole frame."
    ),
}

RECEPTACLE_LADDER: dict[ReceptacleRarity, str] = {
    ReceptacleRarity.POUCH: (
        "The container is a POUCH: a small worn drawstring bag of coarse undyed cloth, "
        "colour #8a7a62. Creased, faded and slightly grubby, cinched shut with plain "
        "twine. Its seal is a simple knot with only a faint coloured glimmer at the "
        "centre. Humble and unremarkable. It is small and occupies only the centre of "
        "the frame."
    ),
    ReceptacleRarity.SACK: (
        "The container is a SACK: a larger burlap sack, colour #a08a5c, of heavy visibly "
        "textured weave, tied shut with a leather cord and a small brass ring. It bulges "
        "with unknown contents. A soft coloured light leaks out from the gap at its neck. "
        "It occupies a little under half the frame."
    ),
    ReceptacleRarity.CHEST: (
        "The container is a CHEST: a wooden chest with iron banding and corner fittings, "
        "warm timber and dark metal, colour #b8863b. A rounded lid and a proper metal "
        "lockplate on the front. The keyhole glows steadily and throws a small pool of "
        "coloured light down the face of the chest. It occupies about half the frame."
    ),
    ReceptacleRarity.SAFE: (
        "The container is a SAFE: a machined metal strongbox of brushed steel and "
        "gunmetal, colour #9aa4b0. Heavy riveted plating, precision seams, and a recessed "
        "circular lock mechanism whose ring and inner channels are lit from within. "
        "Solid, engineered and unsentimental. It occupies about two thirds of the frame."
    ),
    ReceptacleRarity.VAULT: (
        "The container is a VAULT: a massive armoured vault door of dark metal and "
        "polished gold detail, colour #d4af37. Layered concentric locking rings, thick "
        "radial bolts, engraved decorative panels. The whole mechanism is threaded with "
        "glowing channels that pulse outward from the centre, and light spills from every "
        "seam. Immovable and expensive. It fills most of the frame."
    ),
    ReceptacleRarity.SANCTUM: (
        "The container is a SANCTUM: barely a container at all, but a floating reliquary "
        "shrine. A dark ornate monolith core with arched sacred architecture, wrapped in "
        "concentric rotating rings of inscribed metal that hover unattached around it. A "
        "vertical seam of pure light runs through its centre, too bright to look at "
        "directly. Motes and shards orbit it and the air around it glows. It reads as a "
        "temple rather than a box. It is enormous and fills the whole frame."
    ),
}

# --- subjects ---
# Colours mirror ELEMENT_COLOR in frontend/src/scene/colors.ts. They must stay
# in sync: the same element rendered in two different hues reads as two
# different things when the icon sits next to the three.js scene.

ELEMENT_HEX: dict[Element, str] = {
    Element.SPACE: "#6c5cf5",
    Element.AIR: "#8fd3f4",
    Element.FIRE: "#f2643d",
    Element.WATER: "#3d9bf2",
    Element.EARTH: "#7a9b52",
    Element.HARMONY: "#f5e06c",
    Element.GROWTH: "#5fbf7a",
    Element.FORGE: "#c8622f",
    Element.DUST: "#a89880",
    Element.MOUNTAIN: "#8a8f9c",
    Element.STEAM: "#c3d8e8",
    Element.MIST: "#9fb6c8",
    Element.OCEAN: "#2a7fa8",
    Element.LIGHTNING: "#f0d040",
    Element.SUN: "#f5a623",
    Element.WIND: "#a8d8c0",
}

ELEMENT_MOTIF: dict[Element, str] = {
    Element.SPACE: "deep violet void with a faint star field visible inside the material",
    Element.AIR: "pale sky blue and weightless, with visible currents flowing through it",
    Element.FIRE: "ember orange, glowing coals and combustion, heat radiating off it",
    Element.WATER: "clear deep blue, fluid and moving, refracting the light passing through",
    Element.EARTH: "mossy green and brown, dense soil and stone, flecked with lichen and grit",
    Element.HARMONY: "warm gold and white, five distinct coloured strands braided into one whole",
    Element.GROWTH: "living green, with roots and new shoots winding through the material",
    Element.FORGE: "molten copper and smelted metal, hammer-marked and still cooling",
    Element.DUST: "pale tan, fine granular particulate suspended and drifting in the air",
    Element.MOUNTAIN: "grey stone of immense mass and permanence, sheer geological faces",
    Element.STEAM: "pale blue-white vapour under pressure, jetting, hot and expanding",
    Element.MIST: "soft grey-blue haze, a veil half concealing whatever is inside it",
    Element.OCEAN: "deep teal of the abyss, immense still pressure and darkness below",
    Element.LIGHTNING: "electric yellow, forked discharge arcing and crackling across gaps",
    Element.SUN: "amber gold and pure radiance, a light source rather than a lit object",
    Element.WIND: "pale mint, unbound spiralling motion that never settles",
}

VIRTUE_MOTIF: dict[Virtue, str] = {
    Virtue.NURTURING: "tending and care, with living vines growing over the container",
    Virtue.DETERMINATION: "hammered and unyielding, dented all over but never broken",
    Virtue.ADAPTABILITY: "shifting and reconfiguring, with parts that have clearly moved",
    Virtue.PRESENCE: "grounded and immovable, weighty and rooted in place",
    Virtue.TRANSFORMATION: "caught mid change of state, one half becoming something else",
    Virtue.REFLECTION: "mirrored surfaces showing back a softened image",
    Virtue.SERENITY: "perfect stillness, calm deep water, entirely undisturbed",
    Virtue.INSPIRATION: "the sudden strike, a flash caught mid arc",
    Virtue.VITALITY: "warmth and life radiating outward, healthy and vivid",
    Virtue.FREEDOM: "unbound and open, its straps loosened, ready to fly apart",
}


@dataclass(frozen=True)
class IconJob:
    """One image to generate."""

    name: str
    """Filename stem, matching the backend's stock keys: e.g. "fire_fragment"."""

    category: str
    """"collectables" or "receptacles" — the output subdirectory."""

    prompt: str
    seed: int

    @property
    def relative_path(self) -> str:
        return f"{self.category}/{self.name}.png"


def _seed_for(subject: str) -> int:
    """A stable seed per subject, shared by all six of its rarities.

    Same seed plus a same-style prompt gives the six tiers a family resemblance
    in composition and lighting, which is most of what makes them read as one
    element at different powers rather than six unrelated objects.
    """
    digest = hashlib.sha256(subject.encode()).hexdigest()
    return int(digest[:8], 16)


def collectable_prompt(element: Element, rarity: CollectableRarity) -> str:
    subject = (
        f"The object is made of the element {element.value.lower()}: "
        f"{ELEMENT_MOTIF[element]}. Its colour is {ELEMENT_HEX[element]}."
    )
    return " ".join([STYLE, subject, COLLECTABLE_LADDER[rarity], OUTPUT])


def receptacle_prompt(virtue: Virtue, rarity: ReceptacleRarity) -> str:
    key_element = VIRTUE_ELEMENT[virtue]
    subject = (
        f"A sealed container holding a hidden reward, themed on the virtue "
        f"{virtue.value.lower()}: {VIRTUE_MOTIF[virtue]}. Its lock and the light leaking "
        f"from inside it glow in the colour {ELEMENT_HEX[key_element]}, "
        f"the colour of {key_element.value.lower()}."
    )
    return " ".join([STYLE, subject, RECEPTACLE_LADDER[rarity], OUTPUT])


def all_jobs() -> list[IconJob]:
    """Every icon to generate, collectables first, in a stable order."""
    jobs: list[IconJob] = []

    for element in Element:
        seed = _seed_for(element.value)
        for rarity in CollectableRarity:
            jobs.append(
                IconJob(
                    name=f"{element.value.lower()}_{rarity.name.lower()}",
                    category="collectables",
                    prompt=collectable_prompt(element, rarity),
                    seed=seed,
                )
            )

    for virtue in Virtue:
        seed = _seed_for(virtue.value)
        for rarity in ReceptacleRarity:
            jobs.append(
                IconJob(
                    name=f"{virtue.value.lower()}_{rarity.name.lower()}",
                    category="receptacles",
                    prompt=receptacle_prompt(virtue, rarity),
                    seed=seed,
                )
            )

    return jobs


def _self_check() -> None:
    """Fail loudly if a subject table has drifted from the enums."""
    missing_hex = set(Element) - set(ELEMENT_HEX)
    missing_motif = set(Element) - set(ELEMENT_MOTIF)
    missing_virtue = set(Virtue) - set(VIRTUE_MOTIF)
    if missing_hex or missing_motif or missing_virtue:
        raise RuntimeError(
            "prompts.py is out of sync with core.enums: "
            f"missing hex {missing_hex}, missing motif {missing_motif}, "
            f"missing virtue {missing_virtue}"
        )
    if len(COLLECTABLE_LADDER) != len(CollectableRarity):
        raise RuntimeError("COLLECTABLE_LADDER does not cover every CollectableRarity")
    if len(RECEPTACLE_LADDER) != len(ReceptacleRarity):
        raise RuntimeError("RECEPTACLE_LADDER does not cover every ReceptacleRarity")


_self_check()


if __name__ == "__main__":
    jobs = all_jobs()
    print(f"{len(jobs)} icons\n")
    for job in jobs[:2]:
        print(f"--- {job.relative_path}  (seed {job.seed}) ---")
        print(job.prompt)
        print()
