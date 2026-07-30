# icongen

Generates the 156 game icons — 96 collectables and 60 receptacles — locally
with FLUX.1-dev. Art direction lives in [docs/ICON_PROMPTS.md](../../docs/ICON_PROMPTS.md);
this directory is the machinery that runs it.

This is a one-off asset pipeline, not part of the app. It has its own venv so
that ~5GB of CUDA wheels never lands in the backend's dependency tree.

## Why the model is quantized, and why Q3_K_S specifically

FLUX.1-dev is a 12B-parameter transformer: 23.8GB in fp16, plus a 9.8GB T5
text encoder. That does not fit on this machine's disk, and the transformer
alone is far larger than 8GB of VRAM. So the transformer is loaded
GGUF-quantized and offloaded to system RAM between denoising steps.

Measured on this card (`bench.py`), Q4_K_S (6.8GB) is not just softer than
Q3_K_S — it is **17x slower**: 55.3 s/step versus 3.2 s/step. At 6.8GB of
weights there is so little VRAM left for activations that Windows pages GPU
memory out to system RAM on every step. Q3_K_S (5.2GB) leaves enough headroom
to actually stay resident, which is the difference between a 5-hour batch and
a 67-hour one. This is a hardware ceiling, not a quality preference — on a
card with more VRAM, Q4 or Q5 would be the better default.

`--offload sequential` (finer-grained, lower peak VRAM) is **not available**
with a GGUF transformer in diffusers 0.39: moving a quantized parameter to the
meta device drops its quant type and raises `KeyError: None`. `model` offload
is the only offload mode that works here.

Two phases keep peak memory down further: `encode` runs the ~10GB of text
encoders once for every prompt and caches the result; `render` then loads only
the ~5.2GB transformer. Holding both stages resident at once measured at
~17GB and reliably segfaulted inside `c10.dll` on this machine's 32GB of RAM
(see `_prompt_fingerprint` in `generate.py` for how the cache invalidates
itself if a prompt changes).

## Setup

```bash
python -m venv .venv
./.venv/Scripts/python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
./.venv/Scripts/python.exe -m pip install -r requirements.txt
```

FLUX.1-dev is a **gated** model. Accept the licence at
[huggingface.co/black-forest-labs/FLUX.1-dev](https://huggingface.co/black-forest-labs/FLUX.1-dev),
then either set `HF_TOKEN` or run `huggingface-cli login`.

Note the licence is **non-commercial**. Fine for a personal build; if LifU is
ever monetized these assets have to be regenerated with FLUX.1-schnell
(Apache-2.0) or replaced.

## Running

```bash
./.venv/Scripts/python.exe generate.py --list          # what would be made
./.venv/Scripts/python.exe generate.py --only fire_*   # one element, 6 tiers
./.venv/Scripts/python.exe generate.py                 # all 156
./.venv/Scripts/python.exe postprocess.py --keep-raw   # chroma key + downscale
```

`generate.py` is resumable: it skips any icon whose PNG already exists, so an
interrupted run continues where it stopped. Seeds derive from the subject name
rather than a counter, so regenerating one icon reproduces it exactly and all
six tiers of an element share a seed — which is most of what makes them read
as one element at different powers.

Output lands in `frontend/public/icons/{collectables,receptacles}/`, named to
match the backend's stock keys (`fire_fragment.png`), so the frontend can look
an icon up from a stock key without a hand-maintained mapping table.

## Post-processing

`postprocess.py` cuts the background to transparency and downscales, using
`rembg` (a trained salient-object segmentation model) rather than a colour
key. That started as a plain magenta chroma key, and it did not survive
contact with real output: FLUX does not reliably paint a flat solid
background no matter how the prompt insists on one — it tends toward a
vignette, bleeds the subject's own colour into it, and adds a soft contact
shadow the prompt explicitly asked it not to. A colour threshold cannot
separate that shadow from real background, because both land in the same
colour neighbourhood; a segmentation model does not care what colour the
background turned out to be, so it does not need to. Verified against both a
vignette-and-shadow render and a flatter one — rembg cut both cleanly.

One decision worth knowing about: **framing is never auto-cropped.** The size
difference between a Fragment and a Core is deliberate art direction.
Cropping to the content bounding box would normalise every tier to the same
size and flatten the hierarchy the whole ladder is built on.

Run with `--keep-raw` on the first pass so the untouched renders survive in
`icons/raw/`.
