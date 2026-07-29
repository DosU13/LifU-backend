"""Generate the LifU icon set locally with FLUX.1-dev.

Why the model is quantized: FLUX.1-dev is a 12B transformer. In fp16 the
weights alone are 23.8GB on disk and will not load into an 8GB card. This
script loads a GGUF-quantized transformer (~7GB) and offloads it to system RAM
between steps, which is what makes the model runnable on consumer hardware at
the cost of speed.

Resumable by design: an icon whose PNG already exists is skipped, so an
interrupted run picks up exactly where it stopped. Seeds are derived from the
subject name, not from a counter, so a regenerated icon is byte-identical to
the one it replaces.

    python generate.py --list
    python generate.py --only fire_* --size 768
    python generate.py                      # all 156
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

import torch
from diffusers import FluxPipeline, FluxTransformer2DModel, GGUFQuantizationConfig

from prompts import IconJob, all_jobs

REPO = "black-forest-labs/FLUX.1-dev"
GGUF_REPO = "city96/FLUX.1-dev-gguf"

DEFAULT_OUT = Path(__file__).resolve().parents[2] / "frontend" / "public" / "icons"


def _resolve_gguf_url(quant: str) -> str:
    return f"https://huggingface.co/{GGUF_REPO}/blob/main/flux1-dev-{quant}.gguf"


def load_pipeline(quant: str, offload: str) -> FluxPipeline:
    """Build the FLUX pipeline with a quantized transformer and CPU offload.

    fp16 rather than bf16: this card is Turing (sm_75), which has no native
    bf16 support, so bf16 would silently fall back to a slow emulated path.
    """
    print(f"[load] transformer {quant} from {GGUF_REPO}", flush=True)
    transformer = FluxTransformer2DModel.from_single_file(
        _resolve_gguf_url(quant),
        quantization_config=GGUFQuantizationConfig(compute_dtype=torch.float16),
        torch_dtype=torch.float16,
    )

    print(f"[load] text encoders + VAE from {REPO}", flush=True)
    pipe = FluxPipeline.from_pretrained(
        REPO,
        transformer=transformer,
        torch_dtype=torch.float16,
    )

    # The transformer is larger than free VRAM, so it cannot simply live on the
    # GPU. "model" offload moves whole components between RAM and VRAM and is
    # much faster; "sequential" goes module by module and fits in far less VRAM
    # but is several times slower. Try the fast one and fall back.
    if offload == "sequential":
        pipe.enable_sequential_cpu_offload()
        print("[load] sequential CPU offload", flush=True)
    else:
        pipe.enable_model_cpu_offload()
        print("[load] model CPU offload", flush=True)

    pipe.vae.enable_tiling()
    pipe.set_progress_bar_config(disable=True)
    return pipe


def _looks_broken(image) -> bool:
    """fp16 FLUX occasionally overflows and decodes to a flat or black frame."""
    extrema = image.convert("RGB").getextrema()
    spread = max(hi - lo for lo, hi in extrema)
    return spread < 12


def generate(
    jobs: list[IconJob],
    out_dir: Path,
    size: int,
    steps: int,
    guidance: float,
    quant: str,
    offload: str,
) -> None:
    pipe = load_pipeline(quant, offload)

    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, dict] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())

    started = time.time()
    done = 0
    suspicious: list[str] = []

    for index, job in enumerate(jobs, start=1):
        target = out_dir / job.relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            print(f"[{index}/{len(jobs)}] skip {job.relative_path} (exists)", flush=True)
            continue

        t0 = time.time()
        image = pipe(
            prompt=job.prompt,
            height=size,
            width=size,
            num_inference_steps=steps,
            guidance_scale=guidance,
            generator=torch.Generator("cpu").manual_seed(job.seed),
        ).images[0]
        elapsed = time.time() - t0

        image.save(target)
        done += 1

        flag = ""
        if _looks_broken(image):
            suspicious.append(job.relative_path)
            flag = "  !! near-flat output, regenerate this one"

        manifest[job.name] = {
            **asdict(job),
            "size": size,
            "steps": steps,
            "guidance": guidance,
            "quant": quant,
            "seconds": round(elapsed, 1),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2))

        remaining = len(jobs) - index
        avg = (time.time() - started) / done
        eta_min = remaining * avg / 60
        print(
            f"[{index}/{len(jobs)}] {job.relative_path}  "
            f"{elapsed:.0f}s  eta {eta_min:.0f}m{flag}",
            flush=True,
        )

    print(f"\ngenerated {done} icons in {(time.time() - started) / 60:.1f} min")
    if suspicious:
        print(f"{len(suspicious)} look broken and should be regenerated:")
        for name in suspicious:
            print(f"  {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--size", type=int, default=768, help="square edge in px")
    parser.add_argument("--steps", type=int, default=28)
    parser.add_argument("--guidance", type=float, default=3.5)
    parser.add_argument(
        "--quant",
        default="Q4_K_S",
        help="GGUF level: Q3_K_S (5.2GB, fastest) | Q4_K_S (6.8GB) | Q5_K_S (8.3GB, best)",
    )
    parser.add_argument("--offload", choices=["model", "sequential"], default="model")
    parser.add_argument("--only", help="glob over icon names, e.g. 'fire_*' or '*_core'")
    parser.add_argument("--limit", type=int, help="stop after N icons (for a timing probe)")
    parser.add_argument("--list", action="store_true", help="print the job list and exit")
    args = parser.parse_args()

    jobs = all_jobs()
    if args.only:
        jobs = [j for j in jobs if fnmatch.fnmatch(j.name, args.only)]
    if args.limit:
        jobs = jobs[: args.limit]

    if args.list:
        for job in jobs:
            print(f"{job.relative_path:44} seed={job.seed}")
        print(f"\n{len(jobs)} icons")
        return 0

    if not jobs:
        print("no icons matched", file=sys.stderr)
        return 1

    if not (os.environ.get("HF_TOKEN") or (Path.home() / ".cache/huggingface/token").exists()):
        print(
            "No HuggingFace token found.\n"
            f"{REPO} is a gated repo: accept the licence at\n"
            f"  https://huggingface.co/{REPO}\n"
            "then set HF_TOKEN, or run: huggingface-cli login",
            file=sys.stderr,
        )
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    generate(jobs, args.out, args.size, args.steps, args.guidance, args.quant, args.offload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
