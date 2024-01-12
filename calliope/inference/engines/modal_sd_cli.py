from __future__ import annotations

import io
import time
from pathlib import Path

from modal import Image, Stub, method

stub = Stub("stable-diffusion-cli")

model_id = "runwayml/stable-diffusion-v1-5"
cache_path = "/vol/cache"


def download_models():
    import diffusers
    import torch

    # Download scheduler configuration. Experiment with different schedulers
    # to identify one that works best for your use-case.
    scheduler = diffusers.DPMSolverMultistepScheduler.from_pretrained(
        model_id,
        subfolder="scheduler",
        cache_dir=cache_path,
    )
    scheduler.save_pretrained(cache_path, safe_serialization=True)

    # Downloads all other models.
    pipe = diffusers.StableDiffusionPipeline.from_pretrained(
        model_id,
        revision="fp16",
        torch_dtype=torch.float16,
        cache_dir=cache_path,
    )
    pipe.save_pretrained(cache_path, safe_serialization=True)


image = (
    Image.debian_slim(python_version="3.10")
    .pip_install(
        "accelerate",
        "diffusers[torch]>=0.15.1",
        "ftfy",
        "torchvision",
        "transformers~=4.25.1",
        "triton",
        "safetensors",
    )
    .pip_install(
        "torch==2.0.1+cu117",
        find_links="https://download.pytorch.org/whl/torch_stable.html",
    )
    .pip_install("xformers", pre=True)
    .run_function(download_models)
)
stub.image = image

@stub.cls(gpu="A10G")
class StableDiffusion:
    def __enter__(self):
        import diffusers
        import torch

        torch.backends.cuda.matmul.allow_tf32 = True

        scheduler = diffusers.DPMSolverMultistepScheduler.from_pretrained(
            cache_path,
            subfolder="scheduler",
            solver_order=2,
            prediction_type="epsilon",
            thresholding=False,
            algorithm_type="dpmsolver++",
            solver_type="midpoint",
            denoise_final=True,  # important if steps are <= 10
            low_cpu_mem_usage=True,
            device_map="auto",
        )
        self.pipe = diffusers.StableDiffusionPipeline.from_pretrained(
            cache_path,
            scheduler=scheduler,
            low_cpu_mem_usage=True,
            device_map="auto",
        )
        self.pipe.enable_xformers_memory_efficient_attention()

    @method()
    def run_inference(
        self, prompt: str, steps: int = 20, batch_size: int = 4
    ) -> list[bytes]:
        import torch

        with torch.inference_mode():
            with torch.autocast("cuda"):
                images = self.pipe(
                    [prompt] * batch_size,
                    num_inference_steps=steps,
                    guidance_scale=7.0,
                ).images

        # Convert to PNG bytes
        image_output = []
        for image in images:
            with io.BytesIO() as buf:
                image.save(buf, format="PNG")
                image_output.append(buf.getvalue())
        return image_output

@stub.local_entrypoint()
def entrypoint(
    prompt: str, samples: int = 5, steps: int = 10, batch_size: int = 1
):
    print(
        f"prompt => {prompt}, steps => {steps}, samples => {samples}, batch_size => {batch_size}"
    )

    dir = Path("./stable-diffusion")
    if not dir.exists():
        dir.mkdir(exist_ok=True, parents=True)

    sd = StableDiffusion()
    for i in range(samples):
        t0 = time.time()
        images = sd.run_inference.remote(prompt, steps, batch_size)
        total_time = time.time() - t0
        print(
            f"Sample {i} took {total_time:.3f}s ({(total_time)/len(images):.3f}s / image)."
        )
        for j, image_bytes in enumerate(images):
            output_path = dir / f"output_{j}_{i}.png"
            print(f"Saving it to {output_path}")
            with open(output_path, "wb") as f:
                f.write(image_bytes)

