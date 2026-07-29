# Icon generation prompts

Art direction for the 156 icons: 96 collectables (16 elements × 6 rarities) and
60 receptacles (10 virtues × 6 rarities).

One image generation call per **subject** — 16 element calls + 10 virtue calls =
**26 calls total**. Each call produces a horizontal strip of all 6 rarities, so
the tiers are drawn side by side in a single pass and escalate coherently
instead of drifting apart across separate calls.

## How to assemble a prompt

Concatenate four blocks, in this order:

```
[STYLE]  +  [SUBJECT]  +  [RARITY LADDER]  +  [OUTPUT]
```

`STYLE`, `RARITY LADDER` and `OUTPUT` are **verbatim constants** — never
reword them between calls, even slightly. They are the only thing keeping 26
independently generated images in the same visual world. `SUBJECT` is the one
line that changes.

## The escalation principle

Read this before editing any rarity text.

Rarity must escalate on **silhouette, light, and implied motion** — *not* on
detail. These render at 64–96px in the inventory grid. Fine filigree is
invisible at that size, so "more ornate" reads as "muddier". What survives
downscaling is outline shape, how much of the tile is lit, and colour contrast.
So each tier up gets a more complex outline, more emitted light, and more of
the frame filled — and only incidentally more detail.

The other rule: all six tiers of one subject must be recognisably **the same
thing**. A Fire Fragment and a Fire Core share hue, motif, and family
resemblance. The player should read the element from across the room and the
tier from the light.

## Block 1 — STYLE (verbatim, every call)

```
Game inventory icon set, painted 3D-render style with clean readable
silhouettes. Semi-realistic fantasy materials — stone, metal, glass, contained
energy. Single light source from upper left, soft ambient bounce, subtle rim
light. Rich saturated colour, deep contrast, no outlines or cel shading. Object
centred, three-quarter view, floating with no ground plane and no cast shadow.
Painterly but crisp — every form readable as a solid shape at small size. No
text, no numbers, no letters, no watermark, no border, no UI frame.
```

## Block 2 — SUBJECT (the one line that changes)

For collectables:

```
Subject: the element {ELEMENT}. Core colour {HEX}. Motif: {MOTIF}.
All six objects are unmistakably the same element — same hue family, same
motif — separated only by tier.
```

For receptacles:

```
Subject: a container holding a hidden reward, themed on the virtue {VIRTUE}.
Container colour {RARITY HEX, per tier below}. Its lock and inner glow are
{KEY ELEMENT} coloured, {KEY HEX} — this is the key it opens with. Motif:
{MOTIF}. All six are unmistakably the same virtue, separated only by tier.
```

Subject tables are at the bottom of this file.

## Block 3a — RARITY LADDER, collectables (verbatim)

```
Six objects in one row, left to right, ascending power:

1. FRAGMENT — a small chipped piece broken off something larger. Rough matte
   mineral, dull and unpolished, dusty surface, one irregular chunk with
   fractured edges. The element's colour is present but muted, as if seen
   through stone. Emits no light at all. Reads as something found on the
   ground. Smallest object in the row, occupying about a third of its tile.

2. SHARD — a cleaner cleaved splinter with two or three flat fracture planes.
   Semi-translucent along the thin edges, a faint sheen catching the light.
   The element's colour is now clearly visible in the interior. Still inert —
   it reflects light but does not produce any. Slightly larger than the
   Fragment.

3. CRYSTAL — a deliberate faceted geometric solid, cut and symmetrical rather
   than broken. Glassy translucent body with a soft internal glow beginning at
   its centre. A thin polished metal band wraps its base — the first sign of
   craft. Faint colour bleeds onto the surface beneath it. Half the tile.

4. ESSENCE — the element is no longer solid: it is contained. A refined
   teardrop or spindle form of clear crystal holding the element in visibly
   liquid, swirling, living motion inside. Held in an ornate metal setting with
   engraved detail. It emits real light now, casting coloured illumination onto
   its own frame, with a few slow motes drifting free around it. Two thirds of
   the tile.

5. SOUL — the containment is straining. A bright nucleus pulses at the centre
   with a visible heartbeat, wrapped in a broken shell whose pieces float apart
   in slow orbit, held by force rather than structure. A luminous aura spills
   past the object's edge and lights the surrounding air. Cracks in the shell
   leak light in hard beams. Fills most of the tile.

6. CORE — a contained star. Perfect radial symmetry, a blindingly bright origin
   point at the centre, ringed by concentric floating sacred-geometry structures
   of dark metal inscribed with glowing lines. Multiple orbits of debris circle
   at different angles. Space visibly distorts and bends around it, the
   surrounding air is charged with drifting particulate, and light floods the
   entire tile edge to edge. It reads as an artifact older than the world. Fills
   the tile completely and is by far the most massive silhouette in the row.
```

## Block 3b — RARITY LADDER, receptacles (verbatim)

```
Six containers in one row, left to right, ascending power. Each is closed and
sealed, with a visible keyhole or seal glowing in the key colour:

1. POUCH — a small worn drawstring bag of coarse undyed cloth, colour #8a7a62.
   Creased, faded, slightly grubby, cinched shut with plain twine. The seal is a
   simple knot with a faint coloured glimmer at its centre. Humble and
   unremarkable. Smallest object in the row.

2. SACK — a larger burlap sack, colour #a08a5c, heavier weave with visible
   texture, tied with a leather cord and a small brass ring. It bulges with
   unknown contents. A soft coloured light leaks from the gap at its neck.

3. CHEST — a wooden chest with iron banding and corner fittings, warm timber and
   dark metal, colour #b8863b. Rounded lid, a proper metal lockplate on the
   front. The keyhole glows steadily in the key colour, throwing a small pool of
   coloured light down the chest's face.

4. SAFE — a machined metal strongbox, brushed steel and gunmetal, colour
   #9aa4b0. Heavy riveted plating, precision seams, a recessed circular lock
   mechanism. The lock's ring and inner channels are lit from within in the key
   colour. Solid, engineered, unsentimental.

5. VAULT — a massive armoured vault door, dark metal and polished gold detail,
   colour #d4af37. Layered concentric locking rings, thick radial bolts,
   engraved decorative panels. The whole mechanism is threaded with glowing key-
   coloured channels that pulse outward from the centre, and light spills from
   every seam. Immovable and expensive. Fills most of the tile.

6. SANCTUM — barely a container any more: a floating reliquary shrine. A dark
   ornate monolith core with arched sacred architecture, wrapped in concentric
   rotating rings of inscribed metal that hover unattached. A vertical seam of
   pure key-coloured light runs through its centre, too bright to look at
   directly. Motes and shards orbit it, the air around it glows, and the light
   floods the entire tile. It reads as a temple, not a box. Fills the tile
   completely and is by far the most massive silhouette in the row.
```

## Block 4 — OUTPUT (verbatim, every call)

```
Layout: exactly six objects in a single horizontal row, evenly spaced, each
centred in its own equal invisible square cell, none touching or overlapping.
Uniform empty margin around every object.

Background: completely flat solid magenta #FF00FF, absolutely uniform, no
gradient, no vignette, no texture, no shadows on the background. The magenta
must not appear anywhere in the objects themselves.

Wide aspect ratio, 6:1. High resolution.
```

Ask for flat magenta rather than transparency — most models fake alpha channels
badly, and a chroma key is trivial to strip cleanly afterwards. Nothing in the
element or virtue palettes is near magenta, so the key never eats real pixels.

## Locking style across the 26 calls

Generating the strips independently is where consistency dies. Pin them:

1. Generate one subject first — **Fire** is a good calibration target, it has
   the widest tonal range. Iterate until the six-tier ladder genuinely reads as
   escalating.
2. Keep that image. For every subsequent call, pass it back as a **style
   reference** — Midjourney `--sref <url>`, or attach it as a reference image on
   whatever tool you use — with the same seed where the tool allows it.
3. Change only the SUBJECT line between calls. If you find yourself rewording
   the ladder to fix one element, fix it in this file and regenerate everything,
   rather than letting one subject diverge.
4. After all 26, view the tier-5 icons together as a set. If any element's Core
   looks weaker than its neighbours, that one gets regenerated — the top tier is
   where inconsistency is most visible to a player.

## Checking the result

Two tests, both quick and both non-negotiable:

- **Downscale test.** Shrink a strip to 64px per icon. Can you still tell tier 1
  from tier 2, and tier 4 from tier 5? If two adjacent tiers collapse into the
  same blob, the escalation is riding on detail instead of silhouette and light.
- **Squint test.** Blur the strip heavily. The six should still form a clear
  ramp of brightness and mass, left to right.

## Slicing and naming

Cut each strip into six squares and name them to match the keys the backend
already emits, so the frontend can look up an icon without a hand-maintained
mapping table. `serialize_stocks()` in
[api/serializers.py](../backend/api/serializers.py) keys stocks as
`"{ELEMENT}_{RARITY}"`:

```
frontend/public/icons/collectables/fire_fragment.png
frontend/public/icons/collectables/fire_core.png
frontend/public/icons/receptacles/serenity_safe.png
```

Lowercase, underscore-separated, matching the enum names in
[core/enums.py](../backend/core/enums.py) exactly.

## Subject table — elements

Colours are the existing `ELEMENT_COLOR` values from
[frontend/src/scene/colors.ts](../frontend/src/scene/colors.ts). Keep them in
sync: the icons and the three.js scene must agree, or the same element reads as
two different things in one screen.

| Element | Hex | Motif |
|---|---|---|
| SPACE | `#6c5cf5` | Deep violet void, a star field visible inside the material, the colour of absence and distance |
| AIR | `#8fd3f4` | Pale sky blue, weightless, visible currents flowing through the body of it |
| FIRE | `#f2643d` | Ember orange, glowing coals and combustion, heat radiating off the surface |
| WATER | `#3d9bf2` | Clear deep blue, fluid and moving, refracting the light passing through it |
| EARTH | `#7a9b52` | Mossy green-brown, dense soil and stone, a little lichen and grit |
| HARMONY | `#f5e06c` | Warm gold-white, five distinct coloured strands braided into one balanced whole |
| GROWTH | `#5fbf7a` | Living green, roots and new shoots winding through the material |
| FORGE | `#c8622f` | Molten copper, smelted metal, hammer-marked and still cooling |
| DUST | `#a89880` | Pale tan, fine particulate suspended in the air, granular and drifting |
| MOUNTAIN | `#8a8f9c` | Grey stone, immense mass and permanence, sheer geological faces |
| STEAM | `#c3d8e8` | Pale blue-white vapour under pressure, jetting, hot and expanding |
| MIST | `#9fb6c8` | Soft grey-blue haze, a veil half-concealing what is inside |
| OCEAN | `#2a7fa8` | Deep teal, the abyss, immense still pressure and darkness below |
| LIGHTNING | `#f0d040` | Electric yellow, forked discharge, arcing and crackling across gaps |
| SUN | `#f5a623` | Amber gold, pure radiance, a light source rather than a lit object |
| WIND | `#a8d8c0` | Pale mint, unbound motion, spiralling and never settling |

## Subject table — virtues

Each receptacle's lock glows in its key element's colour, so a player can see
which key it needs before reading a word. That mapping is `VIRTUE_ELEMENT` in
[core/mappings.py](../backend/core/mappings.py).

| Virtue | Key element | Key hex | Motif |
|---|---|---|---|
| NURTURING | Growth | `#5fbf7a` | Tending and care, living vines growing over the container |
| DETERMINATION | Forge | `#c8622f` | Hammered and unyielding, dented but never broken |
| ADAPTABILITY | Dust | `#a89880` | Shifting and reconfiguring, parts that have clearly moved |
| PRESENCE | Mountain | `#8a8f9c` | Grounded and immovable, weighty and rooted in place |
| TRANSFORMATION | Steam | `#c3d8e8` | Mid-change of state, one half becoming something else |
| REFLECTION | Mist | `#9fb6c8` | Mirrored surfaces, showing back a softened image |
| SERENITY | Ocean | `#2a7fa8` | Perfect stillness, calm deep water, undisturbed |
| INSPIRATION | Lightning | `#f0d040` | The sudden strike, a flash caught mid-arc |
| VITALITY | Sun | `#f5a623` | Warmth and life, radiating outward, healthy and vivid |
| FREEDOM | Wind | `#a8d8c0` | Unbound and open, straps loosened, ready to fly apart |

## Worked example — Fire

The full assembled prompt, ready to paste:

> Game inventory icon set, painted 3D-render style with clean readable
> silhouettes. Semi-realistic fantasy materials — stone, metal, glass, contained
> energy. Single light source from upper left, soft ambient bounce, subtle rim
> light. Rich saturated colour, deep contrast, no outlines or cel shading. Object
> centred, three-quarter view, floating with no ground plane and no cast shadow.
> Painterly but crisp — every form readable as a solid shape at small size. No
> text, no numbers, no letters, no watermark, no border, no UI frame.
>
> Subject: the element FIRE. Core colour #f2643d. Motif: ember orange, glowing
> coals and combustion, heat radiating off the surface. All six objects are
> unmistakably the same element — same hue family, same motif — separated only
> by tier.
>
> Six objects in one row, left to right, ascending power:
>
> 1. FRAGMENT — a small chipped piece broken off something larger. Rough matte
>    mineral, dull and unpolished, dusty surface, one irregular chunk with
>    fractured edges. The element's colour is present but muted, as if seen
>    through stone. Emits no light at all. Reads as something found on the
>    ground. Smallest object in the row, occupying about a third of its tile.
>
> *(…rarity ladder blocks 2–6 as written above…)*
>
> Layout: exactly six objects in a single horizontal row, evenly spaced, each
> centred in its own equal invisible square cell, none touching or overlapping.
> Uniform empty margin around every object.
>
> Background: completely flat solid magenta #FF00FF, absolutely uniform, no
> gradient, no vignette, no texture, no shadows on the background. The magenta
> must not appear anywhere in the objects themselves.
>
> Wide aspect ratio, 6:1. High resolution.
