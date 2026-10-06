"""
The application's navigation rail.

Three destinations in a fixed order, each with its label and its icon. The
rail is a list of places rather than a row of buttons: labels align in a
column, the current page is marked by fill *and* weight *and* ink so the
selection never rests on a background tint alone, and the whole thing can be
narrowed or hidden when the content needs the width. Hidden, it leaves a
thin strip behind holding the one control that brings it back.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QLabel, QSizePolicy, QWidget

from . import layout as ly
from .icons import app_mark, icon
from .theme import Tokens

# key, label, icon name. The order is the navigation order.
PAGES = (
    ("data", "Data", "file-spreadsheet"),
    ("rose", "Wind rose", "compass"),
    ("table", "Frequency table", "table"),
)


def toggle_button(glyph: str, tooltip: str):
    """A square, quiet icon button for showing or hiding the rail."""
    button = ly.button("", variant="quiet")
    button.setIcon(icon(glyph))
    button.setIconSize(QSize(Tokens.ICON_SIZE, Tokens.ICON_SIZE))
    button.setFixedSize(Tokens.CONTROL_HEIGHT, Tokens.CONTROL_HEIGHT)
    button.setToolTip(tooltip)
    return button


class Sidebar(QWidget):
    """Vertical navigation. Emits the index of the page the user picked."""

    selected = Signal(int)
    collapse_requested = Signal()

    MIN_W = 176      # "Frequency table" plus its icon, without eliding
    DEFAULT_W = 208
    MARK_SIZE = 24   # the app mark beside the name, on the 8 px grid

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setMinimumWidth(self.MIN_W)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        panel = ly.vbox(self, margin=Tokens.SPACING_ROW,
                        spacing=Tokens.SPACING_GROUP)

        brand = ly.hbox(spacing=Tokens.SPACING_ROW)
        brand.setContentsMargins(Tokens.SPACING_ROW, Tokens.SPACING_ROW,
                                 Tokens.SPACING_ROW, 0)
        mark = QLabel()
        mark.setPixmap(app_mark(self.MARK_SIZE))
        mark.setFixedSize(self.MARK_SIZE, self.MARK_SIZE)
        brand.addWidget(mark)
        brand.addWidget(ly.brand("Zephyr"))
        brand.addStretch()
        panel.addLayout(brand)

        nav = ly.vbox(spacing=2)   # destinations are one list, so tight
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons = []

        for index, (key, label, glyph) in enumerate(PAGES):
            button = ly.button(label, variant="nav")
            button.setCheckable(True)
            button.setIcon(icon(glyph))
            button.setIconSize(QSize(Tokens.ICON_SIZE, Tokens.ICON_SIZE))
            button.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
            button.setToolTip(label)
            button.clicked.connect(
                lambda _checked, i=index: self.selected.emit(i))
            self._group.addButton(button, index)
            self._buttons.append(button)
            nav.addWidget(button)

        panel.addLayout(nav)
        panel.addStretch()

        footer = ly.hbox()
        footer.addStretch()
        self.collapse_button = toggle_button(
            "chevrons-left", "Hide the navigation (Ctrl+B)")
        self.collapse_button.clicked.connect(self.collapse_requested)
        footer.addWidget(self.collapse_button)
        panel.addLayout(footer)

        self._buttons[0].setChecked(True)

    def set_current(self, index: int) -> None:
        """Mark a page as current without re-emitting the selection."""
        if 0 <= index < len(self._buttons):
            self._buttons[index].setChecked(True)

    def current(self) -> int:
        return self._group.checkedId()


class SidebarStrip(QWidget):
    """What remains of the rail while it is hidden: one button to restore it."""

    expand_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("sidebarStrip")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(Tokens.CONTROL_HEIGHT + 2 * Tokens.SPACING_ROW)

        panel = ly.vbox(self, margin=Tokens.SPACING_ROW)
        panel.addStretch()
        button = toggle_button("chevrons-right",
                               "Show the navigation (Ctrl+B)")
        button.clicked.connect(self.expand_requested)
        panel.addWidget(button)
