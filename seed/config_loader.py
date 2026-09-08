"""Reference-data loader — reads reference.json."""
from __future__ import annotations

import json
from pathlib import Path


def load_reference(path: str | Path) -> dict:
    """Load and return the parsed reference.json."""
    return json.loads(Path(path).read_text(encoding="utf-8"))
