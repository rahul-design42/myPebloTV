"""
Artwork dimension / aspect-ratio / file-size validator.

Rules from reference.json:
  poster    2:3   600×900    ≤ 200 KB
  banner   16:9  1280×720   ≤ 200 KB
  thumbnail 16:9   640×360   ≤ 200 KB

Aspect-ratio tolerance: ±2% relative  (|actual - target| / target ≤ 0.02).
Dimension check: each axis must be within ±2% of the target.

Human-readable errors are returned so a non-technical editor can act on them.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field

from PIL import Image

_SPECS: dict[str, dict] = {
    "poster": {"aspect": (2, 3), "target": (600, 900), "max_kb": 200},
    "banner": {"aspect": (16, 9), "target": (1280, 720), "max_kb": 200},
    "thumbnail": {"aspect": (16, 9), "target": (640, 360), "max_kb": 200},
}

_TOLERANCE = 0.02  # 2%


@dataclass
class ArtworkValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    width: int = 0
    height: int = 0
    size_bytes: int = 0
    format: str = "JPEG"


def validate_artwork(kind: str, data: bytes) -> ArtworkValidationResult:
    """
    Validate image bytes against the spec for *kind*.

    Returns an ArtworkValidationResult.  If .valid is False, .errors contains
    human-readable messages suitable for display to a content editor.
    """
    spec = _SPECS.get(kind)
    if spec is None:
        return ArtworkValidationResult(valid=False, errors=[f"Unknown artwork kind: {kind}"])

    result = ArtworkValidationResult(valid=True, size_bytes=len(data))
    errors: list[str] = []

    # --- File size check ---
    size_kb = len(data) / 1024
    if size_kb > spec["max_kb"]:
        errors.append(
            f"{kind.capitalize()} must be ≤ {spec['max_kb']} KB. "
            f"Your file is {size_kb:.1f} KB."
        )

    # --- Parse image ---
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))  # reopen after verify()
        w, h = img.size
        result.width = w
        result.height = h
        result.format = img.format or "JPEG"
    except Exception as exc:
        errors.append(f"Could not read image file: {exc}")
        result.valid = False
        result.errors = errors
        return result

    # --- Dimension check (each axis ±2%) ---
    tw, th = spec["target"]
    w_ok = abs(w - tw) / tw <= _TOLERANCE
    h_ok = abs(h - th) / th <= _TOLERANCE
    if not (w_ok and h_ok):
        kind_label = kind.capitalize()
        errors.append(
            f"{kind_label} must be approximately {tw}×{th} pixels. "
            f"Your image is {w}×{h}."
        )

    # --- Aspect-ratio check ---
    ar_num, ar_den = spec["aspect"]
    target_ratio = ar_num / ar_den
    actual_ratio = w / h if h else 0
    if abs(actual_ratio - target_ratio) / target_ratio > _TOLERANCE:
        errors.append(
            f"{kind.capitalize()} must have a {ar_num}:{ar_den} aspect ratio. "
            f"Your image ({w}×{h}) has a {actual_ratio:.3f}:1 ratio."
        )

    result.valid = len(errors) == 0
    result.errors = errors
    return result
