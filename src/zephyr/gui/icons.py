"""
The application's single icon family.

One set, one stroke weight, one size. The glyphs are Lucide geometry drawn
on Lucide's native 24 px grid and rendered down to the 16 px icon token, with
the stroke widened to 2.25 so that it lands at exactly 1.5 px once scaled.

Icons are tinted from the ink ladder rather than shipped as coloured assets,
so a new rung in ``theme.py`` reaches them without touching any artwork. An
icon is never the only carrier of meaning here - every one of these sits
beside its own text label.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from .theme import Tokens


# The application's own mark, kept apart from the glyph family above: it is
# artwork with its own fill, not a tinted line icon. A PyInstaller bundle
# unpacks it beside this module, so the frozen root is checked too.
def _assets_dir() -> Path:
    beside_module = Path(__file__).parent / "assets"
    if beside_module.is_dir():
        return beside_module
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root) / "zephyr" / "gui" / "assets"
    return beside_module


ASSETS_DIR = _assets_dir()
APP_ICON_SVG = ASSETS_DIR / "zephyr.svg"
APP_ICON_ICO = ASSETS_DIR / "zephyr.ico"


def app_icon() -> QIcon:
    """The window and taskbar icon, from the multi-size .ico."""
    return QIcon(str(APP_ICON_ICO))


def app_mark(size: int, ratio: float = 2.0) -> QPixmap:
    """The application mark rendered crisp at ``size`` logical pixels."""
    renderer = QSvgRenderer(str(APP_ICON_SVG))
    pixmap = QPixmap(int(size * ratio), int(size * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pixmap

# Lucide paths on a 24x24 grid. Keep new entries in the same idiom: round
# caps and joins, geometric construction, no fills.
_GLYPHS = {
    # The workbook the observations are read from
    "file-spreadsheet": (
        '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
        '<path d="M14 2v4a2 2 0 0 0 2 2h4"/>'
        '<path d="M8 13h2"/><path d="M14 13h2"/>'
        '<path d="M8 17h2"/><path d="M14 17h2"/>'
    ),
    # Direction: the rose itself
    "compass": (
        '<circle cx="12" cy="12" r="10"/>'
        '<polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>'
    ),
    # The frequencies behind the diagram, as numbers
    "table": (
        '<rect width="18" height="18" x="3" y="3" rx="2"/>'
        '<path d="M3 9h18"/><path d="M3 15h18"/><path d="M12 3v18"/>'
    ),
    # The affordance on every combo box and spin box. Qt's QSS cannot build
    # a triangle out of collapsed borders - it draws each border on its own
    # and the result reads as a dash - so the arrows come from the icon set
    # like every other glyph in the app.
    "chevron-down": ('<path d="m6 9 6 6 6-6"/>'),
    "chevron-up": ('<path d="m18 15-6-6-6 6"/>'),
    # The sidebar toggle: collapse the rail, and bring it back
    "chevrons-left": (
        '<path d="m11 17-5-5 5-5"/><path d="m18 17-5-5 5-5"/>'
    ),
    "chevrons-right": (
        '<path d="m6 17 5-5-5-5"/><path d="m13 17 5-5-5-5"/>'
    ),
}

_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
    'fill="none" stroke="{colour}" stroke-width="2.25" '
    'stroke-linecap="round" stroke-linejoin="round">{body}</svg>'
)


def _pixmap(name: str, colour: str, size: int, ratio: float) -> QPixmap:
    """Render one glyph at the given device pixel ratio."""
    svg = _SVG.format(colour=colour, body=_GLYPHS[name])
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))

    pixmap = QPixmap(int(size * ratio), int(size * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    # Render into an explicit logical rect: with no target given, the SVG is
    # laid out against the pixmap's device rect and the glyph overflows its
    # box by the device pixel ratio.
    renderer.setAspectRatioMode(Qt.KeepAspectRatio)
    renderer.render(painter, QRectF(0, 0, size, size))
    painter.end()
    return pixmap


def icon(name: str, *, size: int = 0, ratio: float = 2.0) -> QIcon:
    """An icon that sits at glyph alpha and promotes when active.

    Qt picks the ``On`` pixmap for a checked button and the ``Active`` one
    under the mouse, so a nav item's icon brightens with its label instead
    of staying flat while the text around it changes.
    """
    if name not in _GLYPHS:
        raise KeyError(
            f"No '{name}' in the icon set. Add it to _GLYPHS in Lucide's "
            f"idiom, or use a text label - never reach for a second family."
        )
    size = size or Tokens.ICON_SIZE
    rest = Tokens.ink_hex(Tokens.INK_GLYPH)
    active = Tokens.ink_hex(Tokens.INK_SECONDARY)
    selected = Tokens.ink_hex(Tokens.INK_PRIMARY)

    result = QIcon()
    result.addPixmap(_pixmap(name, rest, size, ratio),
                     QIcon.Normal, QIcon.Off)
    result.addPixmap(_pixmap(name, active, size, ratio),
                     QIcon.Active, QIcon.Off)
    result.addPixmap(_pixmap(name, selected, size, ratio),
                     QIcon.Normal, QIcon.On)
    result.addPixmap(_pixmap(name, selected, size, ratio),
                     QIcon.Active, QIcon.On)
    result.addPixmap(_pixmap(name, Tokens.ink_hex(Tokens.INK_DISABLED),
                             size, ratio), QIcon.Disabled, QIcon.Off)
    return result


# ---------------------------------------------------------------------------
# QSS cannot tint an image, so the arrow assets are rendered per rung and
# referenced by path. Qt picks the @2x file itself on a high-DPI screen.
# ---------------------------------------------------------------------------

_ARROW_RUNGS = {
    "rest": Tokens.INK_GLYPH,
    "disabled": Tokens.INK_DISABLED,
}


def arrow_assets(size: int = 10) -> dict:
    """Write the chevrons QSS needs and return their paths.

    Returns ``{"<glyph>_<rung>": "<forward-slashed path>"}``, empty if the
    cache cannot be written - the stylesheet then falls back to Qt's own
    arrows rather than the app losing its drop-downs entirely.
    """
    cache = Path(tempfile.gettempdir()) / "pyside6_nordic_arrows"
    paths = {}
    try:
        cache.mkdir(parents=True, exist_ok=True)
        for glyph in ("chevron-down", "chevron-up"):
            for rung, alpha in _ARROW_RUNGS.items():
                colour = Tokens.ink_hex(alpha)
                for ratio, suffix in ((1.0, ""), (2.0, "@2x")):
                    path = cache / f"{glyph}-{rung}-{size}{suffix}.png"
                    _pixmap(glyph, colour, size, ratio).save(str(path), "PNG")
                paths[f"{glyph}_{rung}"] = (
                    cache / f"{glyph}-{rung}-{size}.png").as_posix()
    except OSError:
        return {}
    return paths
