# icongen

Generates the 156 game icons — 96 collectables and 60 receptacles — locally
with FLUX.1-dev. Art direction lives in [docs/ICON_PROMPTS.md](../../docs/ICON_PROMPTS.md);
this directory is the machinery that runs it.

This is a one-off asset pipeline, not part of the app. It has its own venv so
that ~5GB of CUDA wheels never lands in the backend's dependency tree.

## Why the model is quantized

FLUX.1-dev is a 12B-parameter transformer: 23.8GB in fp16, plus a 9.8GB T5
text encoder. That does not fit on this machine's disk, and the transformer
alone is far larger than 8GB of VRAM. So the transformer is loaded
GGUF-quantized (~7GB at Q4_K_S) and offloaded to system RAM between denoising
steps. That is the trade that makes a 12B model runnable on a 2070, and it
costs speed — minutes per image rather than seconds.

Quantization levels, if you want to trade quality against VRAM:

| Level | Size | Notes |
|---|---|---|
| `Q3_K_S` | 5.2GB | Fits VRAM most comfortably, visibly softer |
| `Q4_K_S` | 6.8GB | Default — the usual quality/size sweet spot |
| `Q5_K_S` | 8.3GB | Best, needs `--offload sequential` on an 8GB card |

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

`postprocess.py` cuts the flat magenta background to transparency and
downscales. Two decisions in there worth knowing about:

- **Background is found by connectivity, not colour.** Space is `#6c5cf5` and
  several glows are violet — close enough to magenta that a plain colour key
  punches holes through the artwork. Only magenta regions reachable from the
  image border are treated as background.
- **Framing is never auto-cropped.** The size difference between a Fragment and
  a Core is deliberate. Cropping to the content bounding box would normalise
  every tier to the same size and flatten the hierarchy.

Run with `--keep-raw` on the first pass so the untouched renders survive in
`icons/raw/` if the key needs retuning.
