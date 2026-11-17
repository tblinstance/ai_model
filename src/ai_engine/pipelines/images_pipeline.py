"""Image synthesis pipeline combining vectorized spatial fields with Pillow rendering."""

from __future__ import annotations

import hashlib
import numpy as np
from PIL import Image, ImageDraw

from ..models import BaseAIModel, EnsembleInference
from ..schemas import GenerationRequest, TaskType
from .base_pipeline import BasePipeline
from .media_renderer import (
    apply_prompt_colormap,
    array_to_image,
    decode_reference_image,
    encode_image,
    enhance_image,
    pillow_capabilities,
)
from .photorealistic_portrait import render_photorealistic_portrait


class ImagesPipeline(BasePipeline):
    """Generates styled images from neural spatial fields and Pillow enhancements."""

    task = TaskType.IMAGES

    @staticmethod
    def _palette_from_prompt(prompt: str) -> tuple[np.ndarray, np.ndarray]:
        digest = hashlib.sha256(prompt.encode("utf-8")).digest()
        c1 = np.array([digest[0], digest[1], digest[2]], dtype=np.float32) / 255.0
        c2 = np.array([digest[3], digest[4], digest[5]], dtype=np.float32) / 255.0
        # Keep vibrant luminance contrast
        c1 = 0.25 + c1 * 0.7
        c2 = 0.2 + c2 * 0.75
        return c1, c2

    def _execute(
        self,
        model: BaseAIModel,
        request: GenerationRequest,
        encoding: EnsembleInference,
    ) -> dict[str, object]:
        default_w, default_h = model.spec.image_resolution
        width = request.width or default_w
        height = request.height or default_h

        spatial, used_backends = model.synthesize_spatial(
            prompt=request.prompt,
            width=width,
            height=height,
            backend_override=request.backend,
            seed=request.seed,
        )
        c1, c2 = self._palette_from_prompt(request.prompt)

        # Blend neural spatial channels with prompt-conditioned chromatic & perceptual colormap
        luma = spatial.mean(axis=2, keepdims=True)
        tinted = spatial * 0.55 + (luma * c1 + (1.0 - luma) * c2) * 0.45
        colormapped, cmap_name = apply_prompt_colormap(tinted, request.prompt, tint_strength=0.42)

        raw_ref = request.metadata.get("reference_image_base64")
        if not raw_ref and isinstance(request.metadata.get("reference_frames_base64"), list):
            frames_list = request.metadata["reference_frames_base64"]
            raw_ref = frames_list[0] if frames_list else None

        ref_decoded = (
            decode_reference_image(str(raw_ref), target_size=(width, height))
            if raw_ref
            else None
        )
        reference_info = None

        lowered_prompt = request.prompt.lower()
        is_human = any(
            k in lowered_prompt
            for k in (
                "man", "woman", "person", "human", "face", "portrait", "girl",
                "boy", "guy", "lady", "female", "male", "character", "actor",
                "actress", "model", "people", "avatar", "trump", "donald",
                "donail", "dunal", "donalt", "tum", "trum", "caricature", "parody", "celebrity", "president",
            )
        )

        if ref_decoded is not None:
            ref_rgb, reference_info = ref_decoded
            blended_output = np.clip(ref_rgb * 0.62 + colormapped * 0.38, 0.0, 1.0).astype(np.float32)
            image = enhance_image(array_to_image(blended_output, smooth=False), contrast=1.1, color=1.15)
        elif is_human:
            # High-fidelity photorealistic portrait synthesis for human prompts
            is_trump = any(w in lowered_prompt for w in ("trump", "donald", "donail", "dunal", "donalt", "tum", "trum"))
            is_caricature = any(w in lowered_prompt for w in ("caricature", "parody", "funny", "comedy", "cartoon", "satire", "satirical", "meme"))
            is_realistic = any(w in lowered_prompt for w in ("realistic", "real", "realstic", "photo", "photorealistic", "portrait", "hd", "4k", "authentic"))

            if is_trump:
                if is_caricature and not is_realistic:
                    gender_key = "trump_caricature"
                else:
                    gender_key = "trump"
            elif any(w in lowered_prompt for w in ("caricature", "parody")):
                gender_key = "trump_caricature"
            elif any(w in lowered_prompt for w in ("man", "boy", "guy", "male", "gentleman")):
                gender_key = "virtual_man" if "virtual" in lowered_prompt else "man"
            else:
                gender_key = "virtual_woman" if "virtual" in lowered_prompt else "woman"

            portrait_arr = render_photorealistic_portrait(
                width=width,
                height=height,
                gender=gender_key,
                mouth_open=0.0,
                blink=0.0,
            )
            if not any(k in lowered_prompt for k in ("neon", "cyber", "plasma", "inferno", "matrix")):
                cmap_name = "natural_portrait"
                spatial_noise = (luma - 0.5) * 0.03
                blended_output = np.clip(portrait_arr + spatial_noise, 0.0, 1.0).astype(np.float32)
            else:
                blended_output = np.clip(portrait_arr * 0.94 + colormapped * 0.06, 0.0, 1.0).astype(np.float32)
            image = enhance_image(array_to_image(blended_output, smooth=False), contrast=1.04, color=1.06)
        else:
            image = enhance_image(array_to_image(colormapped, smooth=True))

        if not is_human:
            draw = ImageDraw.Draw(image, "RGBA")
            # Add clean neural geometric focal rings from latent vector
            cx, cy = width // 2, height // 2
            for idx, val in enumerate(encoding.latent_vector[:5]):
                radius = int(min(width, height) * (0.12 + idx * 0.08 + abs(val) * 0.05))
                alpha = max(25, 110 - idx * 18)
                offset_x = int(val * width * 0.14)
                offset_y = int(encoding.latent_vector[(idx + 3) % len(encoding.latent_vector)] * height * 0.14)
                bbox = [cx + offset_x - radius, cy + offset_y - radius, cx + offset_x + radius, cy + offset_y + radius]
                draw.ellipse(bbox, outline=(255, 255, 255, alpha), width=2)

        requested_fmt = str(request.metadata.get("format", "PNG"))
        img_bytes, ext, mime_type = encode_image(image, output_format=requested_fmt)

        trained_style = None
        if self.trainer is not None:
            matched, match_score = self.trainer.retrieve_best_match(
                request.prompt,
                task=TaskType.IMAGES,
                min_score=0.52,
            )
            if matched is not None:
                trained_style = {"score": match_score, "preset": matched.response}

        file_path, public_url, preview_b64 = self.storage.save_bytes(
            data=img_bytes,
            subdir="images",
            extension=ext,
            include_base64=True,
        )

        extra: dict[str, object] = {
            "width": width,
            "height": height,
            "format": ext,
            "colormap": cmap_name,
            "renderer": "pillow",
            "pillow_version": pillow_capabilities()["version"],
            "spatial_backends": used_backends,
            "conditioned_on_upload": reference_info is not None,
        }
        if reference_info is not None:
            extra["reference_info"] = reference_info
        if trained_style is not None:
            extra["trained_style"] = trained_style

        source_note = " from uploaded media" if reference_info is not None else ""
        return {
            "text": f"Generated {width}x{height} {ext.upper()} image{source_note} ({cmap_name}) for '{request.prompt}'.",
            "artifact_url": public_url,
            "artifact_path": str(file_path),
            "preview_base64": preview_b64,
            "mime_type": mime_type,
            "extra": extra,
        }

