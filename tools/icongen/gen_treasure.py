"""Generates the single dedicated treasure-chest icon.

The Treasury's chest thumbnails used to borrow a random content's receptacle
art, which is misleading (a chest slot isn't any one virtue/rarity until you
buy). This renders one dedicated icon instead, through the same pipeline and
style block as the other 156 so it belongs in the same visual world.

    python gen_treasure.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from generate import DEFAULT_OUT, encode_prompts, render  # noqa: E402
from postprocess import process  # noqa: E402
from prompts import OUTPUT, STYLE, IconJob, _seed_for  # noqa: E402

SUBJECT = (
    "An ornate overflowing treasure chest of dark aged wood bound in gold, its "
    "lid thrown open, spilling a rich pile of gold coins, cut gems in many "
    "colours, and jewelled trinkets over its front edge. Lush and abundant and "
    "purely inviting -- this is the promise of a prize in general, not any one "
    "specific reward."
)

CLIP_PROMPT = (
    "an open treasure chest overflowing with gold coins and gems, ornate dark "
    "wood and gold banding, fantasy game icon, painted 3D render, centred on a "
    "flat magenta background"
)


def treasure_job() -> IconJob:
    return IconJob(
        name="treasure_chest",
        category="misc",
        prompt=" ".join([STYLE, SUBJECT, OUTPUT]),
        clip_prompt=CLIP_PROMPT,
        seed=_seed_for("treasure_chest"),
    )


def main() -> int:
    job = treasure_job()
    encode_prompts([job])
    render([job], DEFAULT_OUT, size=768, steps=28, guidance=3.5, quant="Q3_K_S", offload="model")

    from rembg import new_session

    print("[postprocess] isnet-general-use segmentation", flush=True)
    session = new_session("isnet-general-use")
    process(DEFAULT_OUT / job.relative_path, session, 256, None)
    print("done:", DEFAULT_OUT / job.relative_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
