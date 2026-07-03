"""Material Icons rendered to themed QIcons.

Loads the bundled Material Icons font once and paints a glyph (by codepoint)
tinted to a given color, so icons match the dark theme, look identical on every
platform (we render them ourselves rather than relying on native OS icons), and
stay crisp at any size.

Only the icons the app uses are listed in CODEPOINTS - that avoids shipping and
parsing the full 2000+ entry codepoints map. To add an icon, look up its hex in
the Material Icons reference and add a `name: 0x...` entry; the bundled font
already contains every glyph.
"""

from __future__ import annotations

import tempfile
from functools import lru_cache
from pathlib import Path

from lexo.gui.qt import (
    QApplication,
    QColor,
    QFont,
    QFontDatabase,
    QIcon,
    QPainter,
    QPixmap,
    QRect,
    Qt,
)
from lexo.infra import paths

# Default tint for menu/toolbar icons; matches the theme's muted label color.
ICON_COLOR = "#c2cdda"

# name -> Material Icons codepoint (keep sorted by name).
CODEPOINTS: dict[str, int] = {
    "account_circle": 0xE853,
    "arrow_downward": 0xE5DB,
    "arrow_upward": 0xE5D8,
    "build": 0xE869,
    "call_split": 0xE0B6,
    "cancel": 0xE5C9,
    "check_box": 0xE834,
    "check_box_outline_blank": 0xE835,
    "check_circle": 0xE86C,
    "chevron_left": 0xE5CB,
    "chevron_right": 0xE5CC,
    "close": 0xE5CD,
    "content_copy": 0xE14D,
    "content_cut": 0xE14E,
    "crop": 0xE3BE,
    "delete": 0xE872,
    "delete_sweep": 0xE16C,
    "description": 0xE873,
    "error": 0xE000,
    "file_copy": 0xE173,
    "file_download": 0xE2C4,
    "fit_screen": 0xEA10,
    "folder_open": 0xE2C8,
    "format_paint": 0xE243,
    "info": 0xE88E,
    "keyboard_arrow_down": 0xE313,
    "keyboard_arrow_up": 0xE316,
    "library_add": 0xE02E,
    "login": 0xEA77,
    "logout": 0xE9BA,
    "photo_library": 0xE413,
    "play_arrow": 0xE037,
    "replay": 0xE042,
    "rotate_left": 0xE419,
    "rotate_right": 0xE41A,
    "save": 0xE161,
    "save_alt": 0xE171,
    "schedule": 0xE8B5,
    "system_update_alt": 0xE8D7,
    "vertical_split": 0xE949,
    "zoom_in": 0xE8FF,
    "zoom_out": 0xE900,
}

_family: str | None = None
_PNG_CACHE: dict[tuple[str, str, int], str] = {}


def _font_family() -> str:
    global _family
    if _family is None:
        font_path = str(paths.bundled_icon("MaterialIcons-Regular.ttf"))
        font_id = QFontDatabase.addApplicationFont(font_path)
        families = QFontDatabase.applicationFontFamilies(font_id)
        _family = families[0] if families else "Material Icons"
    return _family


@lru_cache(maxsize=256)
def material_icon(name: str, color: str = ICON_COLOR, size: int = 18) -> QIcon:
    """A themed QIcon for the named Material icon, or an empty QIcon if unknown."""
    code = CODEPOINTS.get(name)
    if code is None:
        return QIcon()
    app = QApplication.instance()
    dpr = app.devicePixelRatio() if app is not None else 1.0
    px = max(1, round(size * dpr))
    pixmap = QPixmap(px, px)
    pixmap.fill(Qt.transparent)
    font = QFont(_font_family())
    font.setPixelSize(px)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(QRect(0, 0, px, px), Qt.AlignCenter, chr(code))
    painter.end()
    # Set DPR after painting so the glyph renders at full device resolution
    # (crisp on HiDPI) but displays at the logical `size`.
    pixmap.setDevicePixelRatio(dpr)
    return QIcon(pixmap)


def icon_png(name: str, color: str = ICON_COLOR, size: int = 12) -> str:
    """Render a glyph to a cached PNG and return its path (for QSS `image: url`).

    Qt stylesheet sub-control arrows (e.g. QSpinBox::up-arrow) need a real image;
    the CSS border-triangle trick renders as a rectangle. We paint the Material
    glyph to a small PNG once and reuse it.
    """
    key = (name, color, size)
    cached = _PNG_CACHE.get(key)
    if cached is not None and Path(cached).exists():
        return cached
    pixmap = material_icon(name, color, size).pixmap(size, size)
    cache_dir = Path(tempfile.gettempdir()) / "lexo-icons"
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"{name}_{color.lstrip('#')}_{size}.png"
    pixmap.save(str(out), "PNG")
    url = out.as_posix()
    _PNG_CACHE[key] = url
    return url
