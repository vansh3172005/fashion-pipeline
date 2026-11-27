"""AI studio shot on the local GPU (Stable Diffusion 1.5, img2img), used by
pipeline/packshot.py for items the shop only photographs on a model.

The garment cut-out on the off-white backdrop is the starting image, so the
product's colour, shape and print guide the result; Stable Diffusion redraws
it as a clean product-only studio shot (no person, repaired edges). Runs on
the RTX 2050 in float16 (about 2.5 GB of video memory). Needs the GPU
environment: .venv-gpu (torch CUDA + diffusers). Nothing leaves the PC; the
model is downloaded once from Hugging Face.
"""
from functools import lru_cache

from PIL import Image

MODEL = "stable-diffusion-v1-5/stable-diffusion-v1-5"
NEGATIVE = ("person, model, human, body, skin, face, head, neck, hands, arms, legs, mannequin, "
            "hanger, text, watermark, logo overlay, torn, ripped edge, cut off, deformed, "
            "extra sleeves, blurry, low quality, busy background, shadow of a person")


@lru_cache(maxsize=1)
def pipeline():
    import torch
    from diffusers import StableDiffusionImg2ImgPipeline
    pipe = StableDiffusionImg2ImgPipeline.from_pretrained(
        MODEL, torch_dtype=torch.float16, variant="fp16", safety_checker=None,
        requires_safety_checker=False)
    pipe.set_progress_bar_config(disable=True)
    pipe.enable_attention_slicing()
    try:
        pipe.to("cuda")
    except RuntimeError:  # not enough video memory: stream layers from RAM instead
        pipe.enable_model_cpu_offload()
    return pipe


def describe(item) -> str:
    """Prompt from the item's own parameters (colour, pattern, fit, category)."""
    cat = {"tshirt": "t-shirt", "joggers": "jogger pants", "coord_set": "co-ord set",
           "ethnic_bottom": "salwar pants", "kurta": "kurta tunic"}.get(item.get("category"),
                                                                      (item.get("category") or "garment").replace("_", " "))
    colour = (item.get("color_name") or item.get("color") or "").split("/")[0].strip().lower()
    pattern = item.get("pattern") if item.get("pattern") not in (None, "solid") else "plain"
    fit = item.get("fit") if item.get("fit") not in (None, "regular") else ""
    words = " ".join(w for w in (colour, pattern, fit, cat) if w)
    return (f"professional e-commerce studio product photo of a {words}, garment only, "
            "ghost mannequin, neatly shaped, front view, centered, plain off-white background, "
            "soft natural shadow, even studio lighting, high detail fabric texture, sharp focus")


def studio_shot(composed: Image.Image, item, strength=0.55, steps=28, seed=0) -> Image.Image:
    """Redraw a composed cut-out (product on the backdrop) as a studio shot, 512 px."""
    import torch
    pipe = pipeline()
    src = composed.convert("RGB").resize((512, 512), Image.LANCZOS)
    g = torch.Generator(device="cpu").manual_seed(seed)
    out = pipe(prompt=describe(item), negative_prompt=NEGATIVE, image=src, strength=strength,
               num_inference_steps=steps, guidance_scale=7.0, generator=g).images[0]
    return out
