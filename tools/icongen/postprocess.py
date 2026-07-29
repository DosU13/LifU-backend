"""Turn the raw magenta-background renders into transparent, web-sized PNGs.

Two things here are less obvious than they look:

Background detection is by connectivity, not by colour. Space is #6c5cf5 and
Inspiration's glow is bright violet -- both close enough to magenta that a
plain colour key punches holes through the middle of the artwork. Instead the
magenta mask is labelled into connected regions and only those touching the
border are treated as background, so an interior violet highlight survives.

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
from scipy import ndimage

DEFAULT_DIR = Path(__file__).resolve().parents[2] / "frontend" / "public" / "icons"
MAGENTA = np.array([255, 0, 255], dtype=np.float32)


def _background_mask(rgb: np.ndarray, tolerance: int) -> np.ndarray:
    """Pixels that are magenta *and* reachable from the image border."""
    distance = np.linalg.norm(rgb.astype(np.float32) - MAGENTA, axis=-1)
    magenta_like = distance < tolerance

    labels, count = ndimage.label(magenta_like)
    if count == 0:
        return np.zeros(rgb.shape[:2], dtype=bool)

    border = np.concatenate(
        [labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]],
    )
    touching = set(border[border > 0].tolist())
    if not touching:
        return np.zeros(rgb.shape[:2], dtype=bool)

    return np.isin(labels, list(touching))


def _despill(rgb: np.ndarray, edge_band: np.ndarray) -> np.ndarray:
    """Pull magenta fringe out of the cut edge only.

    Restricted to a couple of pixels around the silhouette: applied globally it
    would desaturate every legitimately warm object, and Fire is #f2643d.
    """
    out = rgb.astype(np.float32).copy()
    r, g, b = out[..., 0], out[..., 1], out[..., 2]
    spill = np.minimum(r, b) - g
    active = edge_band & (spill > 0)
    correction = np.where(active, spill, 0.0)
    out[..., 0] -= correction
    out[..., 2] -= correction
    return np.clip(out, 0, 255).astype(np.uint8)


def process(path: Path, size: int, tolerance: int, raw_dir: Path | None) -> None:
    image = Image.open(path).convert("RGB")
    rgb = np.array(image)

    background = _background_mask(rgb, tolerance)
    foreground = ~background

    # A 2px band straddling the silhouette, where magenta has bled into the art.
    grown = ndimage.binary_dilation(foreground, iterations=2)
    shrunk = ndimage.binary_erosion(foreground, iterations=2)
    edge_band = grown & ~shrunk

    rgb = _despill(rgb, edge_band)

    alpha = (foreground * 255).astype(np.uint8)
    alpha_image = Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(0.6))

    if raw_dir is not None:
        raw_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, raw_dir / path.name)

    out = Image.merge("RGBA", (*Image.fromarray(rgb).split(), alpha_image))
    out = out.resize((size, size), Image.LANCZOS)
    out.save(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument("--size", type=int, default=256, help="output edge in px")
    parser.add_argument(
        "--tolerance",
        type=int,
        default=110,
        help="how far from pure magenta still counts as background",
    )
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

    for index, path in enumerate(paths, start=1):
        raw_dir = (args.dir / "raw" / path.parent.name) if args.keep_raw else None
        process(path, args.size, args.tolerance, raw_dir)
        print(f"[{index}/{len(paths)}] {path.parent.name}/{path.name}", flush=True)

    print(f"\nprocessed {len(paths)} icons to {args.size}px with transparency")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
