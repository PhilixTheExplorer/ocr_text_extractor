"""Bundled GUI resources (the app logo and the Myanmar font)."""

from __future__ import annotations

from functools import lru_cache

from lexo.gui.qt import QFontDatabase, QIcon, QPixmap
from lexo.infra.paths import bundled_asset, bundled_font

# Only the regular weight is bundled; nothing renders Burmese in bold, and Qt
# can synthesize a bold face from this if it is ever needed.
_MYANMAR_FONT_FILES = ("NotoSansMyanmar-Regular.ttf",)


def app_icon() -> QIcon:
    return QIcon(str(bundled_asset("lexo.png")))


def logo_pixmap() -> QPixmap:
    return QPixmap(str(bundled_asset("lexo.png")))


@lru_cache(maxsize=1)
def myanmar_font_family() -> str | None:
    """Register the bundled Noto Sans Myanmar faces and return the family name.

    Registering the bundled font means Burmese renders in the GUI even when the
    OS has no Myanmar Unicode font installed. Returns None if loading failed.
    Requires a running QApplication, so call it during GUI startup.
    """
    family: str | None = None
    for filename in _MYANMAR_FONT_FILES:
        font_id = QFontDatabase.addApplicationFont(str(bundled_font(filename)))
        if font_id == -1:
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        if families and family is None:
            family = families[0]
    return family
