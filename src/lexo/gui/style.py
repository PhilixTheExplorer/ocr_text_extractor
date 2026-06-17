"""Application style loading."""

from __future__ import annotations

from importlib import resources


def load_style(name: str = "dark") -> str:
    qss = resources.files("lexo.assets.styles").joinpath(f"{name}.qss").read_text(encoding="utf-8")
    # Substitute real arrow images for the spinbox sub-controls; QSS cannot draw
    # a triangle itself, so we point it at rendered PNGs of the Material glyphs.
    from lexo.gui.icons import icon_png

    qss = qss.replace("__ARROW_UP__", icon_png("keyboard_arrow_up", "#c8d2df", 12))
    qss = qss.replace("__ARROW_DOWN__", icon_png("keyboard_arrow_down", "#c8d2df", 12))
    return qss
