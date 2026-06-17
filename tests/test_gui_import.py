import os

import pytest


def test_gui_module_imports() -> None:
    # The GUI cannot be rendered headless, but importing it catches syntax,
    # import, and wiring errors at module load time.
    from lexo.gui.app import run

    assert callable(run)


def test_bundled_myanmar_font_registers() -> None:
    # Burmese must render even with no Myanmar font on the OS, so the bundled
    # Noto Sans Myanmar has to load. Needs a QApplication; run it offscreen and
    # skip if this environment cannot start Qt at all.
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    try:
        from lexo.gui.qt import QApplication
    except Exception as exc:  # pragma: no cover - Qt not importable
        pytest.skip(f"Qt unavailable: {exc}")

    try:
        app = QApplication.instance() or QApplication([])
    except Exception as exc:  # pragma: no cover - no display backend
        pytest.skip(f"Qt cannot start: {exc}")
    assert app is not None

    from lexo.gui.resources import myanmar_font_family

    assert myanmar_font_family() == "Noto Sans Myanmar"
