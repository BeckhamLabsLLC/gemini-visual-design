"""Gemini API client wrapper with auth, retry, and error handling."""

import asyncio
import logging
import threading
import time
from typing import Any, Optional

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from .config import (
    API_TIMEOUT_MS,
    GEMINI_API_KEY,
    GEMINI_FLASH_TEXT,
    IMAGE_MODELS,
    VEO_3_FAST_MODEL,
    VEO_3_LITE_MODEL,
    VEO_3_MODEL,
    VIDEO_POLL_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)

# Retry configuration for the thin backoff we still do ourselves around
# long-running video polling. Ordinary request retries are handled by the SDK.
MAX_RETRIES = 3
BASE_DELAY = 1.0
MAX_DELAY = 30.0

# How long to wait between video operation polls.
POLL_INTERVAL_SECONDS = 5.0

# HTTP status codes worth retrying. Notably absent: 400 and 404. Retrying a
# malformed request or a retired model id just burns time before failing.
RETRYABLE_STATUS = [408, 429, 500, 502, 503, 504]

# Map friendly model names to API model IDs
VIDEO_MODEL_MAP = {
    "veo-3.1": VEO_3_MODEL,
    "veo-3.1-fast": VEO_3_FAST_MODEL,
    "veo-3.1-lite": VEO_3_LITE_MODEL,
}

# finish_reason values that mean the model refused rather than failed.
BLOCKED_FINISH_REASONS = {
    "SAFETY",
    "PROHIBITED_CONTENT",
    "IMAGE_SAFETY",
    "IMAGE_PROHIBITED_CONTENT",
    "BLOCKLIST",
    "SPII",
    "RECITATION",
    "IMAGE_RECITATION",
}


class GeminiClientError(Exception):
    """Base error for Gemini client operations."""

    pass


class GeminiAuthError(GeminiClientError):
    """Authentication failure."""

    pass


class GeminiQuotaError(GeminiClientError):
    """Quota exceeded."""

    pass


class GeminiContentPolicyError(GeminiClientError):
    """Content blocked by safety policy."""

    pass


def _looks_like_policy_block(err: genai_errors.APIError) -> bool:
    text = f"{getattr(err, 'message', '')} {getattr(err, 'details', '')}".lower()
    return any(token in text for token in ("safety", "prohibited_content", "blocklist", "blocked"))


def _extract_parts(response: Any) -> tuple[list[dict], list[str]]:
    """Pull inline images and text out of a generate_content response.

    Returns (images, texts). Raises GeminiContentPolicyError when the model
    refused, so callers get an actionable message instead of a bare
    "no image data".
    """
    images: list[dict] = []
    texts: list[str] = []

    for candidate in getattr(response, "candidates", None) or []:
        reason = str(getattr(candidate, "finish_reason", "") or "").upper()
        reason = reason.rsplit(".", 1)[-1]
        if reason in BLOCKED_FINISH_REASONS:
            raise GeminiContentPolicyError(
                f"Gemini refused this request (finish_reason={reason}). "
                "Rephrase the prompt and try again."
            )
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", None) or []:
            inline = getattr(part, "inline_data", None)
            if inline is not None and getattr(inline, "data", None):
                images.append({"data": inline.data, "mime_type": inline.mime_type})
            elif getattr(part, "text", None):
                texts.append(part.text)

    feedback = getattr(response, "prompt_feedback", None)
    block_reason = getattr(feedback, "block_reason", None)
    if block_reason and not images and not texts:
        raise GeminiContentPolicyError(
            f"Prompt blocked before generation (block_reason={block_reason})."
        )

    return images, texts


def _require_images(images: list[dict], texts: list[str], what: str) -> list[dict]:
    if images:
        if texts:
            images[0]["text"] = "\n".join(texts)
        return images
    if texts:
        raise GeminiClientError(f"Model returned text instead of {what}: {' '.join(texts)}")
    raise GeminiClientError(f"No {what} data in response")


def _first_text(response: Any, what: str) -> str:
    _, texts = _extract_parts(response)
    if texts:
        return "\n".join(texts)
    raise GeminiClientError(f"No {what} in response")


class GeminiClient:
    """Wrapper around the google-genai SDK for Gemini API operations."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or GEMINI_API_KEY
        if not self._api_key:
            raise GeminiAuthError(
                "GEMINI_API_KEY environment variable not set. "
                "Get your API key at https://aistudio.google.com/apikey"
            )
        self._client = genai.Client(
            api_key=self._api_key,
            http_options=types.HttpOptions(
                timeout=API_TIMEOUT_MS,
                retry_options=types.HttpRetryOptions(
                    attempts=MAX_RETRIES,
                    initial_delay=BASE_DELAY,
                    max_delay=MAX_DELAY,
                    http_status_codes=RETRYABLE_STATUS,
                ),
            ),
        )

    def _sync_call(self, func, *args, **kwargs) -> Any:
        """Run a sync SDK call, translating SDK errors into our own types.

        Transport-level retry is configured on the client, so this only
        classifies what comes back out.
        """
        try:
            return func(*args, **kwargs)
        except genai_errors.ClientError as e:
            code = getattr(e, "code", None)
            if code in (401, 403):
                raise GeminiAuthError(f"Authentication failed: {e}") from e
            if code == 429:
                raise GeminiQuotaError(f"API quota exceeded: {e}") from e
            if _looks_like_policy_block(e):
                raise GeminiContentPolicyError(f"Content blocked by safety policy: {e}") from e
            raise GeminiClientError(f"Request rejected by the Gemini API: {e}") from e
        except genai_errors.ServerError as e:
            raise GeminiClientError(f"Gemini API is unavailable: {e}") from e
        except GeminiClientError:
            raise
        except Exception as e:
            raise GeminiClientError(f"Unexpected error calling the Gemini API: {e}") from e

    def _image_config(
        self, aspect_ratio: str | None, resolution: str | None
    ) -> types.GenerateContentConfig:
        image_config = None
        if aspect_ratio or resolution:
            image_config = types.ImageConfig(
                aspect_ratio=aspect_ratio,
                image_size=resolution,
            )
        return types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=image_config,
        )

    async def generate_image_gemini(
        self,
        prompt: str,
        tier: str = "fast",
        aspect_ratio: str | None = None,
        resolution: str | None = None,
        reference_image_data: bytes | None = None,
        reference_mime_type: str | None = None,
    ) -> list[dict]:
        """Generate one image with the given tier's model.

        All tiers use generate_content, so every tier accepts a reference
        image. Returns a list of dicts with keys 'data', 'mime_type',
        optionally 'text', and 'model' (as reported by the server).
        """
        model_id = IMAGE_MODELS[tier]

        def _call():
            if reference_image_data and reference_mime_type:
                contents = [
                    types.Part.from_bytes(data=reference_image_data, mime_type=reference_mime_type),
                    prompt,
                ]
            else:
                contents = prompt

            return self._client.models.generate_content(
                model=model_id,
                contents=contents,
                config=self._image_config(aspect_ratio, resolution),
            )

        response = await asyncio.to_thread(self._sync_call, _call)
        images, texts = _extract_parts(response)
        results = _require_images(images, texts, "image")
        reported = getattr(response, "model_version", None) or model_id
        for item in results:
            item["model"] = reported
        return results

    async def edit_image_gemini(
        self,
        image_data: bytes,
        mime_type: str,
        instruction: str,
        tier: str = "fast",
    ) -> list[dict]:
        """Edit an image using Gemini's multi-turn image understanding."""
        model_id = IMAGE_MODELS[tier]

        def _call():
            return self._client.models.generate_content(
                model=model_id,
                contents=[
                    types.Part.from_bytes(data=image_data, mime_type=mime_type),
                    instruction,
                ],
                config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
            )

        response = await asyncio.to_thread(self._sync_call, _call)
        images, texts = _extract_parts(response)
        results = _require_images(images, texts, "edited image")
        reported = getattr(response, "model_version", None) or model_id
        for item in results:
            item["model"] = reported
        return results

    async def analyze_image(
        self,
        image_data: bytes,
        mime_type: str,
        analysis_prompt: str,
        response_schema: Any | None = None,
    ) -> str:
        """Analyze an image with a text prompt. Returns text analysis.

        Runs on the text model: this produces a critique, not an image, and
        the image-generation models cost far more for the same job.
        """

        def _call():
            config = types.GenerateContentConfig(response_modalities=["TEXT"])
            if response_schema is not None:
                config.response_mime_type = "application/json"
                config.response_schema = response_schema
            return self._client.models.generate_content(
                model=GEMINI_FLASH_TEXT,
                contents=[
                    types.Part.from_bytes(data=image_data, mime_type=mime_type),
                    analysis_prompt,
                ],
                config=config,
            )

        response = await asyncio.to_thread(self._sync_call, _call)
        return _first_text(response, "analysis text")

    async def generate_text(self, prompt: str) -> str:
        """Generate text-only content (no image input/output)."""

        def _call():
            return self._client.models.generate_content(
                model=GEMINI_FLASH_TEXT,
                contents=prompt,
            )

        response = await asyncio.to_thread(self._sync_call, _call)
        return _first_text(response, "text")

    async def generate_video(
        self,
        prompt: str,
        model: str = "veo-3.1-fast",
        image_data: Optional[bytes] = None,
        image_mime_type: Optional[str] = None,
        duration_seconds: int | None = None,
        resolution: str | None = None,
    ) -> Any:
        """Start async video generation. Returns an operation to poll."""
        if model not in VIDEO_MODEL_MAP:
            raise ValueError(
                f"Unknown video model {model!r}. Choose one of: {', '.join(VIDEO_MODEL_MAP)}."
            )
        model_id = VIDEO_MODEL_MAP[model]

        def _call():
            # Veo accepts a prompt alongside an image input - passing both lets
            # the user guide the animation of an existing reference frame.
            image_arg = (
                types.Image(image_bytes=image_data, mime_type=image_mime_type)
                if image_data and image_mime_type
                else None
            )
            return self._client.models.generate_videos(
                model=model_id,
                prompt=prompt,
                image=image_arg,
                config=types.GenerateVideosConfig(
                    person_generation="allow_all",
                    duration_seconds=duration_seconds,
                    resolution=resolution,
                ),
            )

        return await asyncio.to_thread(self._sync_call, _call)

    async def poll_video_operation(
        self, operation, timeout_seconds: int | None = None
    ) -> list[dict]:
        """Poll a video generation operation until complete.

        Returns list of dicts with keys: 'data' (bytes), 'mime_type' (str)
        """
        # `or` would treat an explicit 0 as unset and wait the full default.
        budget = VIDEO_POLL_TIMEOUT_SECONDS if timeout_seconds is None else timeout_seconds
        # asyncio.to_thread cannot interrupt a running thread, so an abandoned
        # request would otherwise keep a worker polling for the full budget.
        # The loop watches this instead of sleeping straight through.
        cancelled = threading.Event()

        def _poll():
            op = operation
            deadline = time.monotonic() + budget
            while not op.done:
                if cancelled.is_set():
                    raise GeminiClientError("Video polling cancelled by the caller")
                if time.monotonic() >= deadline:
                    raise GeminiClientError(
                        f"Video generation timed out after {budget}s. The job may "
                        "still finish server-side; raise GEMINI_VISUAL_VIDEO_TIMEOUT "
                        "to wait longer."
                    )
                # Wait in one place so cancellation is noticed within a second
                # rather than after the full poll interval.
                if cancelled.wait(POLL_INTERVAL_SECONDS):
                    raise GeminiClientError("Video polling cancelled by the caller")
                op = self._sync_call(self._client.operations.get, op)

            results = []
            generated = getattr(op.response, "generated_videos", None) or []
            for item in generated:
                video = getattr(item, "video", None)
                if video is None:
                    continue
                data = getattr(video, "video_bytes", None)
                if not data:
                    data = self._sync_call(self._client.files.download, file=video)
                if isinstance(data, bytes):
                    results.append({"data": data, "mime_type": "video/mp4"})

            if not results:
                raise GeminiClientError("Video generation finished but returned no video")
            return results

        try:
            return await asyncio.to_thread(_poll)
        except asyncio.CancelledError:
            cancelled.set()
            raise
