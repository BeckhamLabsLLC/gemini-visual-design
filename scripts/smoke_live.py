#!/usr/bin/env python3
"""Live end-to-end smoke test. Spends real money.

Deliberately lives in scripts/ so pytest (testpaths = ["tests"]) can never
collect it, and refuses to run in CI. Mocks cannot tell you that a model id
is retired - only a real call can.

    python scripts/smoke_live.py --dry-run
    python scripts/smoke_live.py --yes
"""

import argparse
import asyncio
import json
import os
import struct
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gemini_visual_mcp.config import IMAGE_MODELS  # noqa: E402
from gemini_visual_mcp.gemini_client import GeminiClient  # noqa: E402

# Per-check cost estimates in USD, from Google's published pricing.
COSTS = {
    "models_list": 0.0,
    "image_draft": 0.034,
    "image_fast": 0.067,
    "image_fast_2k_portrait": 0.101,
    "image_pro": 0.134,
    "image_count_2": 0.134,
    "edit": 0.067,
    "analyze": 0.001,
    "reference_style": 0.067,
    "video_lite_4s": 0.20,
    "bad_model_id": 0.0,
}

PROMPT = "A minimalist mountain range logo, flat vector, two colors, on white"


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""
    model: str = ""
    latency_s: float = 0.0
    cost_usd: float = 0.0
    artifacts: list = field(default_factory=list)


def image_dimensions(data: bytes):
    """Read width/height from PNG or JPEG bytes without a decoder."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", data[16:24])
        return w, h
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB):
                h, w = struct.unpack(">HH", data[i + 5 : i + 9])
                return w, h
            i += 2 + struct.unpack(">H", data[i + 2 : i + 4])[0]
    return None, None


class Smoke:
    def __init__(self, client, outdir: Path):
        self.client = client
        self.outdir = outdir
        self.results: list[CheckResult] = []
        self._first_image: Path | None = None

    def _save(self, name: str, data: bytes, ext: str) -> Path:
        path = self.outdir / f"{name}{ext}"
        path.write_bytes(data)
        return path

    async def _image_check(self, name, tier, aspect_ratio=None, resolution=None, count=1):
        started = time.monotonic()
        results = []
        for _ in range(count):
            results += await self.client.generate_image_gemini(
                prompt=PROMPT, tier=tier, aspect_ratio=aspect_ratio, resolution=resolution
            )
        latency = time.monotonic() - started

        artifacts, detail = [], []
        for idx, item in enumerate(results):
            ext = ".png" if "png" in item["mime_type"] else ".jpg"
            path = self._save(f"{name}_{idx}", item["data"], ext)
            artifacts.append(str(path))
            if self._first_image is None:
                self._first_image = path
            w, h = image_dimensions(item["data"])
            if w:
                detail.append(f"{w}x{h}")
                if aspect_ratio:
                    want = [float(x) for x in aspect_ratio.split(":")]
                    ok_ratio = abs((w / h) - (want[0] / want[1])) < 0.03
                    detail.append(f"aspect {aspect_ratio} {'OK' if ok_ratio else 'IGNORED'}")

        return CheckResult(
            name=name,
            ok=bool(results),
            detail=", ".join(detail),
            model=results[0].get("model", "") if results else "",
            latency_s=round(latency, 1),
            cost_usd=COSTS.get(name, 0.0),
            artifacts=artifacts,
        )

    async def check_models_list(self):
        configured = set(IMAGE_MODELS.values())
        live = {m.name.replace("models/", "") for m in self.client._client.models.list()}
        missing = configured - live
        return CheckResult(
            name="models_list",
            ok=not missing,
            detail=f"missing from API: {sorted(missing)}" if missing else "all configured ids live",
        )

    async def check_image_fast(self):
        return await self._image_check("image_fast", "fast", "16:9", "1K")

    async def check_image_fast_2k_portrait(self):
        return await self._image_check("image_fast_2k_portrait", "fast", "9:16", "2K")

    async def check_image_draft(self):
        return await self._image_check("image_draft", "draft", "1:1", "1K")

    async def check_image_pro(self):
        return await self._image_check("image_pro", "pro", "16:9", "1K")

    async def check_image_count_2(self):
        return await self._image_check("image_count_2", "fast", "1:1", "1K", count=2)

    async def check_edit(self):
        if not self._first_image:
            return CheckResult("edit", False, "no source image from earlier checks")
        data = self._first_image.read_bytes()
        started = time.monotonic()
        results = await self.client.edit_image_gemini(
            image_data=data, mime_type="image/png", instruction="Make the background deep navy"
        )
        path = self._save("edit_0", results[0]["data"], ".png")
        return CheckResult(
            "edit", True, "edited image returned", results[0].get("model", ""),
            round(time.monotonic() - started, 1), COSTS["edit"], [str(path)],
        )

    async def check_analyze(self):
        if not self._first_image:
            return CheckResult("analyze", False, "no source image from earlier checks")
        from gemini_visual_mcp.analyzer import analyze_design

        started = time.monotonic()
        analysis = await analyze_design(self.client, str(self._first_image), focus="overall")
        path = self.outdir / "analysis.json"
        path.write_text(json.dumps(analysis, indent=2))
        has_score = "overall_score" in analysis
        return CheckResult(
            "analyze", has_score,
            f"overall_score={analysis.get('overall_score')} "
            f"issues={len(analysis.get('issues', []))}"
            + ("" if has_score else f" PARSE_ERROR={analysis.get('parse_error')}"),
            latency_s=round(time.monotonic() - started, 1),
            cost_usd=COSTS["analyze"], artifacts=[str(path)],
        )

    async def check_reference_style(self):
        if not self._first_image:
            return CheckResult("reference_style", False, "no source image")
        started = time.monotonic()
        results = await self.client.generate_image_gemini(
            prompt="A lighthouse in the same style",
            tier="pro",
            reference_image_data=self._first_image.read_bytes(),
            reference_mime_type="image/png",
        )
        path = self._save("reference_style_0", results[0]["data"], ".png")
        return CheckResult(
            "reference_style", True, "pro tier accepted a reference image",
            results[0].get("model", ""), round(time.monotonic() - started, 1),
            COSTS["reference_style"], [str(path)],
        )

    async def check_video_lite_4s(self):
        started = time.monotonic()
        op = await self.client.generate_video(
            prompt="A slow aerial pan over calm water at sunrise",
            model="veo-3.1-lite", duration_seconds=4, resolution="720p",
        )
        results = await self.client.poll_video_operation(op)
        data = results[0]["data"]
        path = self._save("video", data, ".mp4")
        return CheckResult(
            "video_lite_4s", data[4:8] == b"ftyp", f"{len(data)} bytes",
            "veo-3.1-lite", round(time.monotonic() - started, 1),
            COSTS["video_lite_4s"], [str(path)],
        )

    async def check_bad_model_id(self):
        """A retired id must fail fast, not after three retries."""
        from gemini_visual_mcp.gemini_client import GeminiClientError

        started = time.monotonic()
        try:
            await self.client.generate_image_gemini(prompt=PROMPT, tier="fast")
        except Exception:
            pass
        calls = {"n": 0}
        original = self.client._client.models.generate_content

        def counting(*a, **kw):
            calls["n"] += 1
            kw["model"] = "imagen-4.0-generate-001"
            return original(*a, **kw)

        self.client._client.models.generate_content = counting
        try:
            await self.client.generate_image_gemini(prompt=PROMPT, tier="fast")
            ok, detail = False, "retired model id did NOT raise"
        except GeminiClientError as e:
            ok = calls["n"] == 1
            detail = f"raised after {calls['n']} call(s): {str(e)[:70]}"
        finally:
            self.client._client.models.generate_content = original
        return CheckResult(
            "bad_model_id", ok, detail, latency_s=round(time.monotonic() - started, 1)
        )


CHECK_ORDER = [
    "models_list", "image_fast", "image_fast_2k_portrait", "image_draft",
    "image_pro", "image_count_2", "edit", "analyze", "reference_style",
    "bad_model_id", "video_lite_4s",
]


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="print plan and cost, call nothing")
    parser.add_argument("--yes", action="store_true", help="skip the spend confirmation")
    parser.add_argument("--only", nargs="*", help="run only these checks")
    parser.add_argument("--skip-video", action="store_true")
    args = parser.parse_args()

    if os.environ.get("CI"):
        print("Refusing to spend money in CI.", file=sys.stderr)
        return 2
    if not os.environ.get("GEMINI_API_KEY"):
        print("GEMINI_API_KEY is not set.", file=sys.stderr)
        return 2

    names = args.only or CHECK_ORDER
    if args.skip_video:
        names = [n for n in names if not n.startswith("video")]
    total = sum(COSTS.get(n, 0.0) for n in names)

    print("Planned checks:")
    for n in names:
        print(f"  {n:<26} ~${COSTS.get(n, 0.0):.3f}")
    print(f"  {'TOTAL':<26} ~${total:.2f}\n")
    if args.dry_run:
        return 0
    if not args.yes:
        if input(f"Spend ~${total:.2f}? [y/N] ").strip().lower() != "y":
            return 1

    outdir = Path("smoke-out") / datetime.now().strftime("%Y%m%d_%H%M%S")
    outdir.mkdir(parents=True, exist_ok=True)
    smoke = Smoke(GeminiClient(), outdir)

    spent = 0.0
    for name in names:
        try:
            result = await getattr(smoke, f"check_{name}")()
        except Exception as e:
            result = CheckResult(name, False, f"{type(e).__name__}: {str(e)[:160]}")
        smoke.results.append(result)
        spent += result.cost_usd
        mark = "PASS" if result.ok else "FAIL"
        extra = f" [{result.model}]" if result.model else ""
        print(f"  {mark}  {name:<26} {result.latency_s:>5.1f}s  ${spent:>5.2f}{extra}")
        if result.detail:
            print(f"         {result.detail}")

    (outdir / "results.json").write_text(
        json.dumps([asdict(r) for r in smoke.results], indent=2)
    )
    failed = [r.name for r in smoke.results if not r.ok]
    print(f"\nArtifacts: {outdir}\nSpent ~${spent:.2f}")
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
