"""The Data page: which workbook, which columns, which rows.

This is the per-file setup step. It ends in one primary action - Load data -
and reports what it read rather than leaving the user to guess, so a wrong
column name is visible here instead of surfacing as a modal three steps
later.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (QComboBox, QLabel, QLineEdit, QScrollArea,
                               QSizePolicy, QSpinBox, QWidget)

from zephyr.gui import layout as ly
from zephyr.gui.theme import Tokens as T


class PathLabel(QLabel):
    """A file path elided in the middle, so the filename always survives.

    Eliding the tail of a path hides the one part the user identifies it by.
    The full path is always in the tooltip.
    """

    def __init__(self, placeholder: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self._full = ""
        self._placeholder = placeholder
        self.setProperty("role", "caption")
        self.setWordWrap(False)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.set_path("")

    def set_path(self, path: str) -> None:
        self._full = path
        self.setToolTip(path or self._placeholder)
        self._render()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._render()

    def _render(self):
        text = self._full or self._placeholder
        metrics = QFontMetrics(self.font())
        super().setText(metrics.elidedText(text, Qt.ElideMiddle,
                                           max(self.width() - 4, 40)))


class DataPage(QWidget):
    """Column mapping and row range for one Excel workbook."""

    # The three column fields plus their labels, at the field floor width.
    MIN_W = 340
    # A form is read down a column. Stretched across a wide window the label
    # and its field end up an inch apart and the eye loses the pairing.
    CONTENT_MAX_W = 660

    browse_requested = Signal()
    load_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumWidth(self.MIN_W)

        outer = ly.vbox(self, spacing=0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        outer.addWidget(scroll)

        holder = QWidget()
        body, column = ly.panel(spacing=T.SPACING_SECTION)
        body.setMinimumWidth(self.MIN_W)
        body.setMaximumWidth(self.CONTENT_MAX_W)
        holder_row = ly.hbox(holder)
        # The form grows to its measure and then stops; the spacer keeps it
        # on the leading edge instead of centring it as the window widens.
        holder_row.addWidget(body, 1)
        holder_row.addStretch(1)
        scroll.setWidget(holder)
        self._scroll = scroll

        column.addLayout(self._source_section())
        column.addLayout(self._columns_section())
        column.addLayout(self._rows_section())

        self.load_button = ly.button("Load data", variant="primary",
                                     on_click=self.load_requested.emit)
        self.load_button.setEnabled(False)
        column.addLayout(ly.action_row(self.load_button))

        self.status = ly.status_label()
        column.addWidget(self.status)
        column.addLayout(self._summary_section())
        column.addStretch(1)

    # ------------------------------------------------------------------
    # Sections
    # ------------------------------------------------------------------
    def _source_section(self):
        section = ly.vbox()
        section.addWidget(ly.heading("Source"))
        self.browse_button = ly.button(
            "Choose Excel file…", on_click=self.browse_requested.emit,
            tooltip="Pick the workbook holding the wind observations")
        row = ly.hbox()
        row.addWidget(self.browse_button)
        self.path_label = PathLabel("No file chosen yet")
        row.addWidget(self.path_label, 1)
        section.addLayout(row)
        return section

    def _columns_section(self):
        section = ly.vbox()
        section.addWidget(ly.heading("Columns"))
        section.addWidget(ly.caption(
            "Names are taken from the workbook once a file is chosen. Type a "
            "name if the heading you need is not offered."))
        form = ly.form()
        self.date_time_col = self._column_choice("Date & Time")
        self.wind_speed_col = self._column_choice("Wind Speed")
        self.wind_dir_col = self._column_choice("Wind Direction")
        form.addRow(ly.field_label("Date and time"), self.date_time_col)
        form.addRow(ly.field_label("Wind speed"), self.wind_speed_col)
        form.addRow(ly.field_label("Wind direction"), self.wind_dir_col)
        section.addLayout(form)
        return section

    def _column_choice(self, default: str) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.NoInsert)
        combo.setCurrentText(default)
        return ly.choice_field(combo)

    def _rows_section(self):
        section = ly.vbox()
        section.addWidget(ly.heading("Rows and dates"))
        form = ly.form()

        self.first_row = QSpinBox()
        self.first_row.setRange(0, 1_000_000)
        self.first_row.setToolTip("Zero-based index of the first row to read")
        self.last_row = QSpinBox()
        self.last_row.setRange(0, 1_000_000)
        self.last_row.setSpecialValueText("End of file")
        self.last_row.setToolTip("Leave at 'End of file' to read to the last row")
        form.addRow(ly.field_label("First data row"), ly.value_field(self.first_row))
        form.addRow(ly.field_label("Last data row"), ly.value_field(self.last_row))

        self.date_format = QLineEdit("yyyy-MM-dd HH:mm:ss")
        form.addRow(ly.field_label("Date format"), ly.value_field(self.date_format))
        section.addLayout(form)
        section.addWidget(ly.caption(
            "Examples: yyyy-MM-dd HH:mm:ss, MM/dd/yyyy HH:mm, yyyyMMdd:HHmmss. "
            "Columns already stored as dates are used as they are."))
        return section

    def _summary_section(self):
        section = ly.vbox()
        section.addWidget(ly.heading("What was read"))
        self.summary = ly.results_table(
            ["Field", "Value"], stretch_last=False,
            empty_text="Choose a workbook and select Load data to see what "
                       "was read from it.")
        # Six rows plus the header, so the summary never scrolls a fact
        # out of sight when it is the whole point of the section.
        self.summary.setMinimumHeight(7 * T.CONTROL_HEIGHT + 8)
        section.addWidget(self.summary)
        return section

    # ------------------------------------------------------------------
    # State the window drives
    # ------------------------------------------------------------------
    def set_path(self, path: str) -> None:
        self.path_label.set_path(path)

    def set_columns(self, names) -> None:
        """Offer the workbook's own headings without discarding typed text."""
        for combo in (self.date_time_col, self.wind_speed_col, self.wind_dir_col):
            typed = combo.currentText()
            combo.clear()
            combo.addItems([str(n) for n in names])
            match = combo.findText(typed, Qt.MatchFixedString)
            combo.setCurrentIndex(match) if match >= 0 else combo.setCurrentText(typed)
        self.load_button.setEnabled(True)

    def config(self) -> dict:
        return {
            "date_col": self.date_time_col.currentText().strip(),
            "speed_col": self.wind_speed_col.currentText().strip(),
            "dir_col": self.wind_dir_col.currentText().strip(),
            "first_row": self.first_row.value(),
            "last_row": self.last_row.value(),
            "date_format": self.date_format.text().strip(),
        }

    def set_summary(self, rows) -> None:
        ly.fill_table(self.summary, rows)
        if rows:
            # The summary is the answer to the action that was just taken;
            # leaving it below the fold hides the confirmation.
            self._scroll.ensureWidgetVisible(self.summary)

    def set_status(self, text: str, role: str = "") -> None:
        ly.set_status(self.status, text, role)

    def busy_controls(self):
        """Everything that feeds a load, disabled together while one runs."""
        return [self.browse_button, self.load_button, self.date_time_col,
                self.wind_speed_col, self.wind_dir_col, self.first_row,
                self.last_row, self.date_format]

    def reset(self) -> None:
        self.set_path("")
        self.load_button.setEnabled(False)
        self.summary.setRowCount(0)
        self.set_status("")
