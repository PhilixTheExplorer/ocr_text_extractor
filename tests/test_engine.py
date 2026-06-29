import asyncio

import pytest

from helpers import FakeProvider, make_images
from lexo.domain.events import Event, PageCompleted, PageFailed, RunCompleted, RunStarted
from lexo.pipeline.engine import CancellationToken, Cancelled, OcrEngine


def test_runs_all_pages() -> None:
    engine = OcrEngine(FakeProvider(text="T"), concurrency=2, retry_base_delay=0)
    run = asyncio.run(engine.run(make_images(3)))
    assert set(run.results) == {0, 1, 2}
    assert run.results[1].text == "T p1"


def test_emits_lifecycle_events() -> None:
    events: list[Event] = []
    engine = OcrEngine(FakeProvider(), concurrency=1, retry_base_delay=0)
    asyncio.run(engine.run(make_images(2), on_event=events.append))
    assert any(isinstance(e, RunStarted) for e in events)
    assert sum(isinstance(e, PageCompleted) for e in events) == 2
    assert any(isinstance(e, RunCompleted) for e in events)


def test_page_completed_carries_text() -> None:
    events: list[Event] = []
    engine = OcrEngine(FakeProvider(text="T"), concurrency=1, retry_base_delay=0)
    asyncio.run(engine.run(make_images(2), on_event=events.append))
    done = {e.page_index: e.text for e in events if isinstance(e, PageCompleted)}
    assert done == {0: "T p0", 1: "T p1"}


def test_emit_lifecycle_false_suppresses_run_events() -> None:
    events: list[Event] = []
    engine = OcrEngine(FakeProvider(), concurrency=1, retry_base_delay=0)
    run = asyncio.run(engine.run(make_images(2), on_event=events.append, emit_lifecycle=False))
    assert set(run.results) == {0, 1}
    assert not any(isinstance(e, RunStarted | RunCompleted) for e in events)
    assert sum(isinstance(e, PageCompleted) for e in events) == 2


def test_retries_then_succeeds() -> None:
    provider = FakeProvider(fail_times=2)
    engine = OcrEngine(provider, concurrency=1, max_retries=3, retry_base_delay=0)
    run = asyncio.run(engine.run(make_images(1)))
    assert run.results[0].text.startswith("OCR")
    assert provider.calls == 3


def test_failure_records_error_and_emits_event() -> None:
    events: list[Event] = []
    engine = OcrEngine(
        FakeProvider(fail_times=99), concurrency=1, max_retries=2, retry_base_delay=0
    )
    run = asyncio.run(engine.run(make_images(1), on_event=events.append))
    assert run.results == {}
    assert run.failures[0] == "transient failure"
    assert any(isinstance(e, PageFailed) for e in events)


def test_cancellation_raises() -> None:
    token = CancellationToken()
    token.cancel()
    engine = OcrEngine(FakeProvider(), concurrency=1, retry_base_delay=0)
    with pytest.raises(Cancelled):
        asyncio.run(engine.run(make_images(3), token=token))
