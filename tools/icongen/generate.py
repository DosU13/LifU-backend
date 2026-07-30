"""Generate the LifU icon set locally with FLUX.1-dev.

Runs in two phases, which is the whole trick to fitting a 12B model on an 8GB
card with 32GB of RAM:

  encode  loads the T5 + CLIP text encoders (~10GB), encodes all 156 prompts,
          writes the embeddings to disk, and frees the encoders.
  render  loads only the GGUF-quantized transformer (~7GB) and the VAE, and
          renders from those cached embeddings.

Holding both at once needs ~17GB resident and segfaults inside torch on this
machine. Splitting them makes peak memory max(encoder, transformer) instead of
the sum, and is faster besides: T5 runs once per prompt rather than being
shuffled between RAM and VRAM on every image.

Resumable by design: an icon whose PNG already exists is skipped, so an
interrupted run picks up where it stopped. Seeds derive from the subject name
rather than a counter, so regenerating one icon reproduces it exactly.

    python generate.py --list
    python generate.py --only "fire_*"
    python generate.py                      # all 156
"""

from __future__ import annotations

import argparse
import fnmatch
import gc
import hashlib
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

import torch
from diffusers import FluxPipeline, FluxTransformer2DModel, GGUFQuantizationConfig
from safetensors import safe_open
from safetensors.torch import load_file, save_file

from prompts import IconJob, all_jobs

REPO = "black-forest-labs/FLUX.1-dev"
GGUF_REPO = "city96/FLUX.1-dev-gguf"

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE.parents[1] / "frontend" / "public" / "icons"
EMBED_DIR = HERE / ".embeddings"

# FLUX's T5 window. Our prompts run ~280 tokens, so this leaves headroom
# without paying for the full 512 on every cached tensor.
MAX_SEQUENCE_LENGTH = 384


def _free() -> None:
    gc.collect()
    torch.cuda.empty_cache()


# --- phase 1: text encoding ---


def _prompt_fingerprint(job: IconJob) -> str:
    return hashlib.sha256(f"{job.clip_prompt}\x00{job.prompt}".encode()).hexdigest()[:16]


def _is_cached(job: IconJob) -> bool:
    """True only if an embedding exists *and* was made from this exact prompt.

    Without the fingerprint, editing a prompt would silently reuse the old
    embedding and the change would appear to do nothing.
    """
    path = EMBED_DIR / f"{job.name}.safetensors"
    if not path.exists():
        return False
    with safe_open(path, framework="pt") as f:
        return (f.metadata() or {}).get("fingerprint") == _prompt_fingerprint(job)


def encode_prompts(jobs: list[IconJob]) -> None:
    """Encode every prompt once and cache it, then let the encoders go."""
    pending = [j for j in jobs if not _is_cached(j)]
    if not pending:
        print(f"[encode] all {len(jobs)} prompts already cached")
        return

    EMBED_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[encode] loading text encoders for {len(pending)} prompts", flush=True)

    # transformer/vae are explicitly None: this pipeline exists only to run the
    # text encoders, and building the rest would defeat the point of phasing.
    pipe = FluxPipeline.from_pretrained(
        REPO,
        transformer=None,
        vae=None,
        torch_dtype=torch.float16,
    )
    # T5 alone is ~9.8GB, larger than this card's VRAM, so it has to be streamed
    # through the GPU layer by layer rather than resident.
    pipe.enable_sequential_cpu_offload()

    started = time.time()
    for index, job in enumerate(pending, start=1):
        with torch.no_grad():
            # prompt -> CLIP (77 tokens, pooled global vector),
            # prompt_2 -> T5 (the detailed conditioning).
            prompt_embeds, pooled, _ = pipe.encode_prompt(
                prompt=job.clip_prompt,
                prompt_2=job.prompt,
                max_sequence_length=MAX_SEQUENCE_LENGTH,
            )
        save_file(
            {
                "prompt_embeds": prompt_embeds.squeeze(0).to(torch.float16).cpu(),
                "pooled_prompt_embeds": pooled.squeeze(0).to(torch.float16).cpu(),
            },
            EMBED_DIR / f"{job.name}.safetensors",
            metadata={"fingerprint": _prompt_fingerprint(job)},
        )
        print(f"[encode {index}/{len(pending)}] {job.name}", flush=True)

    print(f"[encode] done in {(time.time() - started) / 60:.1f} min", flush=True)

    del pipe
    _free()


# --- phase 2: rendering ---


def _load_render_pipeline(quant: str, offload: str) -> FluxPipeline:
    print(f"[render] transformer {quant} from {GGUF_REPO}", flush=True)
    transformer = FluxTransformer2DModel.from_single_file(
        f"https://huggingface.co/{GGUF_REPO}/blob/main/flux1-dev-{quant}.gguf",
        quantization_config=GGUFQuantizationConfig(compute_dtype=torch.float16),
        torch_dtype=torch.float16,
    )

    # Text encoders stay None — their work is already cached on disk.
    pipe = FluxPipeline.from_pretrained(
        REPO,
        transformer=transformer,
        text_encoder=None,
        text_encoder_2=None,
        tokenizer=None,
        tokenizer_2=None,
        torch_dtype=torch.float16,
    )

    if offload == "sequential":
        pipe.enable_sequential_cpu_offload()
    else:
        pipe.enable_model_cpu_offload()
    print(f"[render] {offload} CPU offload", flush=True)

    pipe.vae.enable_tiling()
    pipe.set_progress_bar_config(disable=True)
    return pipe


def _looks_broken(image) -> bool:
    """fp16 FLUX occasionally overflows and decodes to a flat or black frame."""
    extrema = image.convert("RGB").getextrema()
    return max(hi - lo for lo, hi in extrema) < 12


def render(
    jobs: list[IconJob],
    out_dir: Path,
    size: int,
    steps: int,
    guidance: float,
    quant: str,
    offload: str,
) -> None:
    pending = [j for j in jobs if not (out_dir / j.relative_path).exists()]
    if not pending:
        print(f"[render] all {len(jobs)} icons already exist")
        return

    pipe = _load_render_pipeline(quant, offload)

    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, dict] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())

    started = time.time()
    suspicious: list[str] = []

    for index, job in enumerate(pending, start=1):
        target = out_dir / job.relative_path
        target.parent.mkdir(parents=True, exist_ok=True)

        cached = load_file(EMBED_DIR / f"{job.name}.safetensors")
        prompt_embeds = cached["prompt_embeds"].unsqueeze(0).to("cuda", torch.float16)
        pooled = cached["pooled_prompt_embeds"].unsqueeze(0).to("cuda", torch.float16)

        t0 = time.time()
        image = pipe(
            prompt_embeds=prompt_embeds,
            pooled_prompt_embeds=pooled,
            height=size,
            width=size,
            num_inference_steps=steps,
            guidance_scale=guidance,
            generator=torch.Generator("cpu").manual_seed(job.seed),
        ).images[0]
        elapsed = time.time() - t0

        image.save(target)

        flag = ""
        if _looks_broken(image):
            suspicious.append(job.relative_path)
            flag = "  !! near-flat output, regenerate"

        manifest[job.name] = {
            **asdict(job),
            "size": size,
            "steps": steps,
            "guidance": guidance,
            "quant": quant,
            "seconds": round(elapsed, 1),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2))

        avg = (time.time() - started) / index
        eta_min = (len(pending) - index) * avg / 60
        print(
            f"[render {index}/{len(pending)}] {job.relative_path}  "
            f"{elapsed:.0f}s  eta {eta_min:.0f}m{flag}",
            flush=True,
        )

    print(f"\nrendered {len(pending)} icons in {(time.time() - started) / 60:.1f} min")
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
    # Q3_K_S is not a quality preference, it is the only level that fits. At
    # Q4_K_S the 6.8GB of weights leave so little VRAM that Windows pages GPU
    # memory to system RAM on every activation: measured 55.3 s/step versus
    # 3.2 s/step here, a 17x penalty. See bench.py.
    parser.add_argument(
        "--quant",
        default="Q3_K_S",
        help="GGUF level. Q3_K_S (5.2GB) is the largest that fits 8GB VRAM without paging",
    )
    # Sequential offload is unusable with GGUF in diffusers 0.39: moving a
    # quantized param to the meta device drops its quant_type and raises
    # KeyError: None.
    parser.add_argument("--offload", choices=["model", "sequential"], default="model")
    parser.add_argument("--phase", choices=["encode", "render", "all"], default="all")
    parser.add_argument("--only", help="glob over icon names, e.g. 'fire_*' or '*_core'")
    parser.add_argument("--limit", type=int, help="stop after N icons")
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
            f"No HuggingFace token found. {REPO} is gated: accept the licence at\n"
            f"  https://huggingface.co/{REPO}\n"
            "then set HF_TOKEN, or run: huggingface-cli login",
            file=sys.stderr,
        )
        return 1

    args.out.mkdir(parents=True, exist_ok=True)

    if args.phase in {"encode", "all"}:
        encode_prompts(jobs)
    if args.phase in {"render", "all"}:
        render(jobs, args.out, args.size, args.steps, args.guidance, args.quant, args.offload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
