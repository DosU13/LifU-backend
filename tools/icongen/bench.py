"""Measure real per-step throughput before committing to a long batch.

Prints seconds per denoising step for a given quantization and resolution,
which is the only number that matters for deciding whether 156 icons is a
coffee break or a lost weekend.

    python bench.py --quant Q4_K_S --size 512
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import torch
from diffusers import FluxPipeline, FluxTransformer2DModel, GGUFQuantizationConfig
from safetensors.torch import load_file

from generate import EMBED_DIR, GGUF_REPO, REPO


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quant", default="Q4_K_S")
    parser.add_argument("--size", type=int, default=512)
    parser.add_argument("--steps", type=int, default=4)
    parser.add_argument("--offload", choices=["model", "sequential"], default="model")
    parser.add_argument("--name", default="fire_fragment")
    args = parser.parse_args()

    cached = EMBED_DIR / f"{args.name}.safetensors"
    if not cached.exists():
        raise SystemExit(f"no cached embedding for {args.name}; run generate.py --phase encode")

    t0 = time.time()
    transformer = FluxTransformer2DModel.from_single_file(
        f"https://huggingface.co/{GGUF_REPO}/blob/main/flux1-dev-{args.quant}.gguf",
        quantization_config=GGUFQuantizationConfig(compute_dtype=torch.float16),
        torch_dtype=torch.float16,
    )
    pipe = FluxPipeline.from_pretrained(
        REPO,
        transformer=transformer,
        text_encoder=None,
        text_encoder_2=None,
        tokenizer=None,
        tokenizer_2=None,
        torch_dtype=torch.float16,
    )
    if args.offload == "sequential":
        pipe.enable_sequential_cpu_offload()
    else:
        pipe.enable_model_cpu_offload()
    pipe.set_progress_bar_config(disable=True)
    print(f"load: {time.time() - t0:.0f}s", flush=True)

    emb = load_file(cached)
    prompt_embeds = emb["prompt_embeds"].unsqueeze(0).to("cuda", torch.float16)
    pooled = emb["pooled_prompt_embeds"].unsqueeze(0).to("cuda", torch.float16)

    t1 = time.time()
    pipe(
        prompt_embeds=prompt_embeds,
        pooled_prompt_embeds=pooled,
        height=args.size,
        width=args.size,
        num_inference_steps=args.steps,
        guidance_scale=3.5,
        generator=torch.Generator("cpu").manual_seed(0),
    )
    total = time.time() - t1
    per_step = total / args.steps
    peak = torch.cuda.max_memory_allocated() / 1e9

    print(f"\nquant={args.quant} size={args.size} offload={args.offload}")
    print(f"{total:.1f}s for {args.steps} steps  =  {per_step:.1f} s/step")
    print(f"peak VRAM allocated: {peak:.2f} GB")
    print(f"-> 28 steps = {per_step * 28 / 60:.1f} min/image")
    print(f"-> 156 icons = {per_step * 28 * 156 / 3600:.1f} hours")


if __name__ == "__main__":
    main()
