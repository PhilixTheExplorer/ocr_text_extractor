"""Engine lifecycle events.

The pipeline engine emits a stream of these; UIs (CLI, GUI) subscribe. Engine
code never touches a widget - this is the seam that keeps it UI-agnostic and
thread-safe.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Event:
    """Base engine event."""

    run_id: str


@dataclass(slots=True)
class RunStarted(Event):
    pages_total: int


@dataclass(slots=True)
class PageStarted(Event):
    page_index: int


@dataclass(slots=True)
class PageCompleted(Event):
    page_index: int
    confidence: float


@dataclass(slots=True)
class PageFailed(Event):
    page_index: int
    error: str


@dataclass(slots=True)
class RunCompleted(Event):
    pages_done: int


@dataclass(slots=True)
class RunFailed(Event):
    error: str


@dataclass(slots=True)
class RunCancelled(Event):
    pass
