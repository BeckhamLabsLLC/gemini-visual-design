"""Gemini API client wrapper with auth, retry, and error handling."""

import asyncio
import logging
import time
from typing import Any, Optional

from google import genai
from google.genai import types

from .config import (
    GEMINI_API_KEY,
    GEMINI_FLASH_IMAGE,
    GEMINI_FLASH_TEXT,
    IMAGEN_MODEL,
    VEO_2_MODEL,
    VEO_3_FAST_MODEL,
    VEO_3_MODEL,
)

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
BASE_DELAY = 1.0
MAX_DELAY = 30.0

# Map friendly model names to API model IDs
VIDEO_MODEL_MAP = {
    "veo-2": VEO_2_MODEL,
    "veo-3.1": VEO_3_MODEL,
    "veo-3.1-fast": VEO_3_FAST_MODEL,
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


class GeminiClient:
    """Wrapper around the google-genai SDK for Gemini API operations."""

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or GEMINI_API_KEY
        if not self._api_key:
            raise GeminiAuthError(
                "GEMINI_API_KEY environment variable not set. "
                "Get your API key at https://aistudio.google.com/apikey"
            )
        self._client = genai.Client(api_key=self._api_key)

    async def _retry_async(self, func, *args, **kwargs) -> Any:
        """Execute an async function with exponential backoff retry."""
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Don't retry auth errors
                if "api key" in error_str or "authentication" in error_str or "401" in error_str:
                    raise GeminiAuthError(f"Authentication failed: {e}") from e

                # Don't retry content policy blocks
                if "safety" in error_str or "blocked" in error_str or "policy" in error_str:
                    raise GeminiContentPolicyError(
                        f"Content blocked by safety policy: {e}"
                    ) from e

                # Retry on rate limits and transient errors
                if "429" in error_str or "quota" in error_str:
                    if attempt == MAX_RETRIES - 1:
                        raise GeminiQuotaError(
                            f"API quota exceeded after {MAX_RETRIES} retries: {e}"
                        ) from e

                delay = min(BASE_DELAY * (2**attempt), MAX_DELAY)
                logger.warning(
                    f"Retry {attempt + 1}/{MAX_RETRIES} after error: {e}. "
                    f"Waiting {delay:.1f}s"
                )
                await asyncio.sleep(delay)

        raise GeminiClientError(f"Failed after {MAX_RETRIES} retries: {last_error}")

    def _sync_call(self, func, *args, **kwargs) -> Any:
        """Execute a sync SDK call with retry logic."""
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                if "api key" in error_str or "authentication" in error_str or "401" in error_str:
                    raise GeminiAuthError(f"Authentication failed: {e}") from e

                if "safety" in error_str or "blocked" in error_str or "policy" in error_str:
                    raise GeminiContentPolicyError(
                        f"Content blocked by safety policy: {e}"
                    ) from e

                if "429" in error_str or "quota" in error_str:
                    if attempt == MAX_RETRIES - 1:
                        raise GeminiQuotaError(
                            f"API quota exceeded after {MAX_RETRIES} retries: {e}"
                        ) from e

                delay = min(BASE_DELAY * (2**attempt), MAX_DELAY)
                logger.warning(
                    f"Retry {attempt + 1}/{MAX_RETRIES} after error: {e}. "
                    f"Waiting {delay:.1f}s"
                )
                time.sleep(delay)

        raise GeminiClientError(f"Failed after {MAX_RETRIES} retries: {last_error}")

    async def generate_image_gemini(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
    ) -> list[dict]:
        """Generate image(s) using Gemini native image generation.

        Uses responseModalities: ["TEXT", "IMAGE"] to get inline image data.

        Returns list of dicts with keys: 'data' (bytes), 'mime_type' (str), 'text' (str|None)
        """

        def _call():
            response = self._client.models.generate_content(
                model=GEMINI_FLASH_IMAGE,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                ),
            )
            return response

        response = await asyncio.to_thread(self._sync_call, _call)

        results = []
        text_parts = []

        if response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if part.inline_data:
                            results.append(
                                {
                                    "data": part.inline_data.data,
                                    "mime_type": part.inline_data.mime_type,
                                }
                            )
                        elif part.text:
                            text_parts.append(part.text)

        # Attach any text response to the first result
        if results and text_parts:
            results[0]["text"] = "\n".join(text_parts)
        elif not results and text_parts:
            # Model returned text only (e.g. explaining why it can't generate)
            raise GeminiClientError(
                f"Model returned text instead of image: {' '.join(text_parts)}"
            )
        elif not results:
            raise GeminiClientError("No image data in response")

        return results

    async def generate_image_imagen(
        self,
        prompt: str,
        count: int = 1,
        aspect_ratio: str = "16:9",
    ) -> list[dict]:
        """Generate image(s) using Imagen 4.

        Returns list of dicts with keys: 'data' (bytes), 'mime_type' (str)
        """

        def _call():
            response = self._client.models.generate_images(
                model=IMAGEN_MODEL,
                prompt=prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=count,
                    aspect_ratio=aspect_ratio,
                ),
            )
            return response

        response = await asyncio.to_thread(self._sync_call, _call)

        results = []
        if response.generated_images:
            for img in response.generated_images:
                results.append(
                    {
                        "data": img.image.image_bytes,
                        "mime_type": "image/png",
                    }
                )

        if not results:
            raise GeminiClientError("No images generated by Imagen")

        return results

    async def edit_image_gemini(
        self,
        image_data: bytes,
        mime_type: str,
        instruction: str,
    ) -> list[dict]:
        """Edit an image using Gemini's multi-turn image understanding.

        Sends the image + edit instruction and returns the edited image.

        Returns list of dicts with keys: 'data' (bytes), 'mime_type' (str), 'text' (str|None)
        """

        def _call():
            response = self._client.models.generate_content(
                model=GEMINI_FLASH_IMAGE,
                contents=[
                    types.Part.from_bytes(data=image_data, mime_type=mime_type),
                    instruction,
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                ),
            )
            return response

        response = await asyncio.to_thread(self._sync_call, _call)

        results = []
        text_parts = []

        if response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if part.inline_data:
                            results.append(
                                {
                                    "data": part.inline_data.data,
                                    "mime_type": part.inline_data.mime_type,
                                }
                            )
                        elif part.text:
                            text_parts.append(part.text)

        if results and text_parts:
            results[0]["text"] = "\n".join(text_parts)
        elif not results and text_parts:
            raise GeminiClientError(
                f"Model returned text instead of edited image: {' '.join(text_parts)}"
            )
        elif not results:
            raise GeminiClientError("No edited image data in response")

        return results

    async def analyze_image(
        self,
        image_data: bytes,
        mime_type: str,
        analysis_prompt: str,
    ) -> str:
        """Analyze an image with a text prompt. Returns text analysis."""

        def _call():
            response = self._client.models.generate_content(
                model=GEMINI_FLASH_IMAGE,
                contents=[
                    types.Part.from_bytes(data=image_data, mime_type=mime_type),
                    analysis_prompt,
                ],
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT"],
                ),
            )
            return response

        response = await asyncio.to_thread(self._sync_call, _call)

        if response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    texts = [p.text for p in candidate.content.parts if p.text]
                    if texts:
                        return "\n".join(texts)

        raise GeminiClientError("No analysis text in response")

    async def generate_text(self, prompt: str) -> str:
        """Generate text-only content (no image input/output).

        Uses the Gemini Flash text model for tasks like design token generation
        where no image context is needed.
        """

        def _call():
            response = self._client.models.generate_content(
                model=GEMINI_FLASH_TEXT,
                contents=prompt,
            )
            return response

        response = await asyncio.to_thread(self._sync_call, _call)

        if response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    texts = [p.text for p in candidate.content.parts if p.text]
                    if texts:
                        return "\n".join(texts)

        raise GeminiClientError("No text in response")

    async def generate_video(
        self,
        prompt: str,
        model: str = "veo-2",
        image_data: Optional[bytes] = None,
        image_mime_type: Optional[str] = None,
    ) -> Any:
        """Start async video generation. Returns an operation to poll.

        Args:
            prompt: Video description
            model: One of "veo-2", "veo-3.1", "veo-3.1-fast"
            image_data: Optional reference image bytes
            image_mime_type: MIME type of reference image
        """
        model_id = VIDEO_MODEL_MAP.get(model, VEO_2_MODEL)

        def _call():
            operation = self._client.models.generate_videos(
                model=model_id,
                prompt=prompt if not (image_data and image_mime_type) else None,
                image=types.Image(image_bytes=image_data, mime_type=image_mime_type) if image_data else None,
                config=types.GenerateVideosConfig(
                    person_generation="allow_all",
                ),
            )
            return operation

        return await asyncio.to_thread(self._sync_call, _call)

    async def poll_video_operation(
        self, operation, timeout_seconds: int = 300
    ) -> list[dict]:
        """Poll a video generation operation until complete.

        Args:
            operation: The video generation operation to poll.
            timeout_seconds: Maximum seconds to wait before timing out (default: 300).

        Returns list of dicts with keys: 'data' (bytes), 'mime_type' (str)
        """

        def _poll():
            start = time.monotonic()
            # Poll until complete
            while not operation.done:
                if time.monotonic() - start > timeout_seconds:
                    raise GeminiClientError(
                        f"Video generation timed out after {timeout_seconds}s. "
                        "The operation may still be running — try again later."
                    )
                time.sleep(5)
                operation.reload()

            if operation.response and operation.response.generated_videos:
                results = []
                for video in operation.response.generated_videos:
                    video_data = self._client.files.download(file=video.video)
                    results.append(
                        {
                            "data": video_data,
                            "mime_type": "video/mp4",
                        }
                    )
                return results
            else:
                raise GeminiClientError("Video generation failed or returned no results")

        return await asyncio.to_thread(_poll)
