"""Drift detection for the cross-language telemetry contract.

The telemetry relay's event-name allowlist and batch limit are duplicated
across Python (``course_intelligence/telemetry.py``) and TypeScript
(``studio/src/analytics/events.ts`` and ``studio/src/api/client.ts``).
Updating one side alone silently drops events (unknown names) or rejects
valid batches (oversize limit). These tests parse the TypeScript sources
and assert the constants match the Python definitions, so drift fails
loudly in CI (``uv run pytest``) instead of silently in production.

Keep this test the single enforcement point for the contract: when it
fails, update *both* sides intentionally rather than silencing it.
"""

from __future__ import annotations

import re
from pathlib import Path

import course_intelligence.telemetry as telemetry

# tests/ lives at the repo root, alongside both course_intelligence/ and
# studio/, so this resolves regardless of cwd.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_STUDIO_SRC = _REPO_ROOT / "studio" / "src"

# Matches `const NAME = <int>;` at module scope in TS.
_TS_INT_CONST = re.compile(
    r"^\s*const\s+(?P<name>[A-Z_][A-Z0-9_]*)\s*=\s*(?P<value>\d+)\s*;",
    re.MULTILINE,
)

# Matches trackAction("studio.event.name", ...) call sites, capturing the
# quoted event name. The function definition `export function trackAction(`
# has no string literal after the paren, so it does not match.
_TRACK_ACTION = re.compile(r"trackAction\(\s*(['\"])(?P<event>[^'\"]+)\1")


def _read_studio_source(*parts: str) -> str:
    path = _STUDIO_SRC.joinpath(*parts)
    assert path.is_file(), f"studio source not found: {path}"
    return path.read_text(encoding="utf-8")


def _extract_int_const(source: str, name: str) -> int:
    for m in _TS_INT_CONST.finditer(source):
        if m.group("name") == name:
            return int(m.group("value"))
    raise AssertionError(f"TS const {name!r} not found in source")


def _collect_ts_event_names() -> set[str]:
    """All 'studio.*' event names passed to trackAction() across studio/src.

    Scans the whole tree (not just events.ts) so a direct trackAction call
    added in a component is caught here rather than dropped by the backend.
    """
    names: set[str] = set()
    for path in sorted(_STUDIO_SRC.rglob("*")):
        if path.suffix not in {".ts", ".tsx"}:
            continue
        source = path.read_text(encoding="utf-8")
        for m in _TRACK_ACTION.finditer(source):
            name = m.group("event")
            if name.startswith("studio."):
                names.add(name)
    return names


def test_batch_limit_matches_across_languages():
    """Both TS copies of MAX_EVENTS_PER_REQUEST equal the Python limit.

    events.ts uses it to flush; client.ts uses it to slice batches before
    posting. Both must equal ``_MAX_EVENTS_PER_REQUEST`` or the backend
    rejects larger client batches with 422.
    """
    expected = telemetry._MAX_EVENTS_PER_REQUEST
    events_ts = _read_studio_source("analytics", "events.ts")
    client_ts = _read_studio_source("api", "client.ts")
    assert _extract_int_const(events_ts, "MAX_EVENTS_PER_REQUEST") == expected
    assert _extract_int_const(client_ts, "MAX_EVENTS_PER_REQUEST") == expected


def test_allowed_events_match_ts_emit_set():
    """The Python allowlist and the set of names the studio emits are equal.

    - A TS-emitted name missing from the allowlist would be silently dropped
      by the backend (no error, no event in Loki).
    - An allowlisted name the studio never emits is stale drift.
    Both directions must stay in lockstep, per telemetry.py's comment.
    """
    ts_events = _collect_ts_event_names()
    allowed = set(telemetry._ALLOWED_EVENTS)
    assert ts_events == allowed, (
        "Telemetry event-name contract drifted.\n"
        f"  emitted by TS but not allowlisted (would be dropped): "
        f"{sorted(ts_events - allowed)}\n"
        f"  allowlisted but not emitted by TS (stale): "
        f"{sorted(allowed - ts_events)}"
    )
