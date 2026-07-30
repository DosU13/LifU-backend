"""Turn the raw renders into transparent, web-sized PNGs.

Originally this keyed out a flat magenta background by colour. That failed in
practice: FLUX (especially the Q3 quant this card needs, see generate.py)
does not reliably paint a flat solid background no matter how the prompt
insists -- it tends toward a vignette, bleeds the subject's own colour into
it, and adds a soft contact shadow the prompt explicitly asked it not to. A
fixed colour threshold could not separate that shadow from real background
without also eating into the object, since both land in the same colour
neighbourhood.

Instead this uses rembg (a trained salient-object segmentation network,
isnet-general-use) to find the object regardless of what the background
actually turned out to be. Verified against both a first-draft render (a dark
vignette background with a visible drop shadow) and a more insistent
background prompt (a flat magenta field) -- rembg cut both cleanly, so the
renders already on disk do not need to be regenerated.

Framing is left alone. The size difference between a Fragment and a Core is
deliberate art direction, so this never crops to the content bounding box --
that would normalise every tier to the same size and destroy the hierarchy.

    python postprocess.py                    # all of frontend/public/icons
    python postprocess.py --size 256 --keep-raw
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from rembg import new_session, remove

DEFAULT_DIR = Path(__file__).resolve().parents[2] / "frontend" / "public" / "icons"
MODEL = "isnet-general-use"


def _despill(rgb: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Pull background-colour fringe out of a thin band around the cut edge.

    Restricted to the edge only: applied globally it would desaturate every
    legitimately warm object, and Fire is #f2643d.
    """
    from scipy import ndimage

    foreground = alpha > 16
    grown = ndimage.binary_dilation(foreground, iterations=2)
    shrunk = ndimage.binary_erosion(foreground, iterations=2)
    edge_band = grown & ~shrunk

    out = rgb.astype(np.float32).copy()
    r, g, b = out[..., 0], out[..., 1], out[..., 2]
    # Every background this pipeline has produced skews magenta/warm-dark, so
    # the tell is green sitting well below red and blue.
    spill = np.minimum(r, b) - g
    correction = np.where(edge_band & (spill > 0), spill, 0.0)
    out[..., 0] -= correction
    out[..., 2] -= correction
    return np.clip(out, 0, 255).astype(np.uint8)


def process(path: Path, session, size: int, raw_dir: Path | None) -> None:
    original = Image.open(path).convert("RGB")

    if raw_dir is not None:
        raw_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, raw_dir / path.name)

    cut = remove(original, session=session)  # RGBA
    rgb = np.array(cut.convert("RGB"))
    alpha = np.array(cut.getchannel("A"))

    rgb = _despill(rgb, alpha)
    alpha_image = Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(0.5))

    out = Image.merge("RGBA", (*Image.fromarray(rgb).split(), alpha_image))
    out = out.resize((size, size), Image.LANCZOS)
    out.save(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--size", type=int, default=256, help="output edge in px")
    parser.add_argument(
        "--keep-raw",
        action="store_true",
        help="copy the untouched renders to icons/raw/ before overwriting",
    )
    args = parser.parse_args()

    paths = sorted(
        p
        for p in args.dir.rglob("*.png")
        if "raw" not in p.parts and p.parent.name in {"collectables", "receptacles"}
    )
    if not paths:
        print(f"no icons found under {args.dir}")
        return 1

    print(f"[load] {MODEL} segmentation model", flush=True)
    session = new_session(MODEL)

    for index, path in enumerate(paths, start=1):
        raw_dir = (args.dir / "raw" / path.parent.name) if args.keep_raw else None
        process(path, session, args.size, raw_dir)
        print(f"[{index}/{len(paths)}] {path.parent.name}/{path.name}", flush=True)

    print(f"\nprocessed {len(paths)} icons to {args.size}px with transparency")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
