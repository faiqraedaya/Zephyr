"""The Frequency table page: the numbers behind the diagram.

A readout rather than a workspace, so it carries no primary action of its
own - it follows whatever the Wind rose page last drew, and the Export menu
saves it. The calm share never appears in the table itself, so it is stated
underneath: without it the percentages look as though they should sum to a
hundred and do not.
"""
from __future__ import annotations

from PySide6.QtWidgets import QWidget

from zephyr.core import constants
from zephyr.gui import layout as ly
from zephyr.gui.theme import Tokens as T

_EMPTY = ("No frequencies yet. Draw a wind rose on the Wind rose page and "
          "the table follows it.")


class TablePage(QWidget):
    """The direction x speed frequency table, as drawn."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        column = ly.vbox(self, spacing=T.SPACING_GROUP)

        column.addWidget(ly.heading(
            "Frequency (% of valid observations)"))
        self.table = ly.results_table([f"Speed ({constants.SPEED_UNIT})"],
                                      stretch_last=False, empty_text=_EMPTY)
        column.addWidget(self.table)

        self.summary = ly.caption("")
        column.addWidget(self.summary)
        column.addWidget(ly.caption(
            "Use the Export menu to save these frequencies as Excel, CSV or "
            "XML."))
        # The slack belongs below the readout, not spread between its lines.
        column.addStretch(1)

    def set_table(self, frame, calm_freq: float, calm_below: float,
                  total_valid: int) -> None:
        """Show a frequency table and the calm share that completes it."""
        headers = [f"Speed ({constants.SPEED_UNIT})"] + [str(c) for c in frame.columns]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        numeric = tuple(range(1, len(headers)))
        rows = [[str(index)] + [f"{value:.2f}" for value in row]
                for index, row in zip(frame.index, frame.to_numpy())]
        ly.fill_table(self.table, rows, numeric_columns=numeric)
        self._fit_height()
        self.summary.setText(
            f"Calm (below {calm_below:g} {constants.SPEED_UNIT}) accounts for "
            f"{calm_freq:.1f}% of {total_valid:,} valid observations; the "
            f"table holds the remaining {100 - calm_freq:.1f}%.")

    def _fit_height(self) -> None:
        """Cap the table at the height its rows actually need.

        At most ten speed categories fit here, so a table stretched down the
        window puts its horizontal scrollbar an inch below the last row.
        """
        header = self.table.horizontalHeader()
        rows = self.table.rowCount() * self.table.verticalHeader().defaultSectionSize()
        scrollbar = self.table.horizontalScrollBar()
        chrome = (header.height() if header is not None else T.CONTROL_HEIGHT) + 4
        if scrollbar is not None:
            chrome += scrollbar.sizeHint().height()
        self.table.setMaximumHeight(rows + chrome)

    def reset(self) -> None:
        self.table.setRowCount(0)
        self.table.setMaximumHeight(16777215)
        self.summary.setText("")
