"""Plain text / markdown parser."""

from __future__ import annotations


def extract_text(path: str) -> str:
    """Read a plain text or markdown file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
