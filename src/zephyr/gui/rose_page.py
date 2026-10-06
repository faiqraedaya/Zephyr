"""The Wind rose page: the diagram and the controls that shape it.

The controls that change the diagram sit beside the diagram they change, in
a splitter, so the user never navigates away to adjust a bin count. Speed
boundaries are checked as they are typed and reported inline, under the
action - a modal here would hide the diagram the user is comparing against.
"""
from __future__ import annotations

from PySide6.QtCore import QDateTime, Qt, Signal
from PySide6.QtWidgets import (QComboBox, QDateTimeEdit, QDoubleSpinBox,
                               QGridLayout, QScrollArea, QSpinBox, QWidget)

from zephyr.core import constants, statistics
from zephyr.gui import layout as ly
from zephyr.gui.rose_canvas import RoseCanvas
from zephyr.gui.theme import Tokens as T

_DATE_FORMAT = "yyyy-MM-dd HH:mm:ss"


class RosePage(QWidget):
    """Diagram settings on the left, the rose on the right."""

    # A speed row - the ordinal and its two boundary fields - measures 332 px,
    # and the settings scroll vertically, so the pane also has to carry a
    # scrollbar without pushing that row into a horizontal one.
    CONTROLS_MIN_W = 332 + 20
    # Below this the polar axes, its compass labels and its legend stop being
    # a diagram and become a slot.
    CANVAS_MIN_W = 380

    update_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._ready = False

        self.canvas = RoseCanvas(empty_text="No wind rose yet. Load a "
                                            "workbook on the Data page, then "
                                            "select Update wind rose.")
        self.canvas.setMinimumWidth(self.CANVAS_MIN_W)

        controls = self._controls_pane()
        split = ly.splitter(controls, self.canvas,
                            sizes=[self.CONTROLS_MIN_W + 40, 720],
                            stretch=[0, 1])
        root = ly.vbox(self, spacing=0)
        root.addWidget(split)

        self._rebuild_speed_rows()

    # ------------------------------------------------------------------
    # Controls
    # ------------------------------------------------------------------
    def _controls_pane(self) -> QWidget:
        """Settings scroll; the action and its inline status do not.

        Ten speed categories push the settings past the height of the pane.
        A primary action that scrolls out of reach - taking the validation
        message with it - is the one thing that must not happen, so both
        stay pinned below the scrolling part.
        """
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)

        body, column = ly.panel(spacing=T.SPACING_SECTION)
        # Room for the scrollbar so it never sits on top of a spin button.
        body.setContentsMargins(0, 0, T.SPACING_ROW, 0)
        scroll.setWidget(body)

        column.addLayout(self._period_section())
        column.addLayout(self._diagram_section())
        column.addLayout(self._speed_section())
        column.addStretch(1)

        self.update_button = ly.button("Update wind rose", variant="primary",
                                       on_click=self.update_requested.emit)
        self.update_button.setEnabled(False)
        self.status = ly.status_label()

        pane = QWidget()
        pane.setMinimumWidth(self.CONTROLS_MIN_W)
        stack = ly.vbox(pane, spacing=T.SPACING_GROUP)
        stack.addWidget(scroll, 1)
        stack.addLayout(ly.action_row(self.update_button))
        stack.addWidget(self.status)
        return pane

    def _period_section(self):
        section = ly.vbox()
        section.addWidget(ly.heading("Analysis period"))
        form = ly.form()
        self.start_date = self._date_edit()
        self.end_date = self._date_edit()
        form.addRow(ly.field_label("Start"), ly.value_field(self.start_date))
        form.addRow(ly.field_label("End"), ly.value_field(self.end_date))
        section.addLayout(form)
        section.addWidget(ly.caption("Both ends are included in the analysis."))
        return section

    def _date_edit(self) -> QDateTimeEdit:
        edit = QDateTimeEdit()
        edit.setDisplayFormat(_DATE_FORMAT)
        edit.setCalendarPopup(True)
        return edit

    def _diagram_section(self):
        section = ly.vbox()
        section.addWidget(ly.heading("Diagram"))
        form = ly.form()

        self.dir_bins = QSpinBox()
        self.dir_bins.setRange(4, 36)
        self.dir_bins.setValue(constants.DEFAULT_DIR_BINS)
        self.dir_bins.setToolTip("Number of direction sectors, or petals")

        self.num_speed_cats = QSpinBox()
        self.num_speed_cats.setRange(2, 10)
        self.num_speed_cats.setValue(constants.DEFAULT_NUM_SPEED_CATS)
        self.num_speed_cats.valueChanged.connect(self._rebuild_speed_rows)

        self.color_combo = QComboBox()
        self.color_combo.addItems(constants.COLOR_SCHEMES)
        self.color_combo.setToolTip("Speed is an ordered quantity, so every "
                                    "scheme runs light to dark")

        form.addRow(ly.field_label("Direction sectors"),
                    ly.value_field(self.dir_bins))
        form.addRow(ly.field_label("Speed categories"),
                    ly.value_field(self.num_speed_cats))
        form.addRow(ly.field_label("Colour scheme"),
                    ly.choice_field(self.color_combo))
        section.addLayout(form)
        return section

    def _speed_section(self):
        section = ly.vbox()
        section.addWidget(ly.heading(f"Speed categories ({constants.SPEED_UNIT})"))
        self.speed_grid = ly.grid()
        self.speed_grid.addWidget(
            ly.unit_label(f"From ({constants.SPEED_UNIT})"), 0, 1)
        self.speed_grid.addWidget(
            ly.unit_label(f"To ({constants.SPEED_UNIT})"), 0, 2)
        self.speed_grid.setColumnStretch(1, 1)
        self.speed_grid.setColumnStretch(2, 1)
        section.addLayout(self.speed_grid)
        section.addWidget(ly.caption(
            "Boundaries must increase, so each 'From' matches the previous "
            "'To'. Speeds below the first 'From' are counted as calm. The "
            "top category is open-ended on the diagram; its 'To' is reported "
            "as the highest velocity band in the XML export."))
        self.speed_rows = []
        return section

    def _rebuild_speed_rows(self):
        """Recreate the boundary rows for the current category count."""
        for row in getattr(self, "speed_rows", []):
            for widget in row:
                self.speed_grid.removeWidget(widget)
                widget.deleteLater()
        self.speed_rows = []

        count = self.num_speed_cats.value()
        defaults = constants.default_speed_ranges(count)
        for index in range(count):
            ordinal = ly.caption(str(index + 1))
            ordinal.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            low, high = self._speed_spin(), self._speed_spin()
            low.setValue(defaults[index][0])
            high.setValue(defaults[index][1])
            low.valueChanged.connect(self._validate)
            high.valueChanged.connect(self._validate)
            grid_row = index + 1
            self.speed_grid.addWidget(ordinal, grid_row, 0)
            self.speed_grid.addWidget(low, grid_row, 1)
            self.speed_grid.addWidget(high, grid_row, 2)
            self.speed_rows.append((ordinal, low, high))
        self._validate()

    def _speed_spin(self) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0, 200)
        spin.setDecimals(1)
        spin.setSingleStep(0.5)
        spin.setMinimumHeight(T.CONTROL_HEIGHT)
        return spin

    # ------------------------------------------------------------------
    # Validation and state
    # ------------------------------------------------------------------
    def _validate(self) -> bool:
        """Check the boundaries as they are typed, and report inline."""
        ranges = self.speed_ranges()
        if not ranges:                      # mid-rebuild; nothing to check yet
            return False
        problem = self._first_bad_boundary(ranges)
        ly.set_status(self.status, problem, "error" if problem else "")
        valid = problem == ""
        self.update_button.setEnabled(valid and self._ready)
        return valid

    def _first_bad_boundary(self, ranges) -> str:
        """The first boundary that does not increase, named by category."""
        unit = constants.SPEED_UNIT
        for index, (low, high) in enumerate(ranges):
            if high <= low:
                return (f"Category {index + 1} ends at {high:g} {unit}, which "
                        f"is not above its own start of {low:g} {unit}.")
            if index and low < ranges[index - 1][1]:
                return (f"Category {index + 1} starts at {low:g} {unit} but "
                        f"category {index} ends at {ranges[index - 1][1]:g} "
                        f"{unit}. Each 'From' must be at least the previous "
                        f"'To'.")
        return "" if statistics.speed_edges_from_ranges(ranges) is not None             else ("Speed category boundaries must increase from the first "
                  "category to the last.")

    def speed_ranges(self):
        return [(low.value(), high.value()) for _, low, high in self.speed_rows]

    def set_ready(self, ready: bool) -> None:
        """Enable the action once there is data for it to act on."""
        self._ready = ready
        self._validate()

    def set_date_range(self, start, end) -> None:
        for edit in (self.start_date, self.end_date):
            edit.setDateTimeRange(QDateTime(start), QDateTime(end))
        self.start_date.setDateTime(QDateTime(start))
        self.end_date.setDateTime(QDateTime(end))

    def config(self) -> dict:
        return {
            "start": self.start_date.dateTime().toPython(),
            "end": self.end_date.dateTime().toPython(),
            "n_sectors": self.dir_bins.value(),
            "ranges": self.speed_ranges(),
            "scheme": self.color_combo.currentText(),
        }

    def period_strings(self):
        return (self.start_date.dateTime().toString("yyyy-MM-dd HH:mm"),
                self.end_date.dateTime().toString("yyyy-MM-dd HH:mm"))

    def set_status(self, text: str, role: str = "") -> None:
        ly.set_status(self.status, text, role)

    def busy_controls(self):
        """The whole settings group feeds the computation, so it all locks."""
        controls = [self.update_button, self.start_date, self.end_date,
                    self.dir_bins, self.num_speed_cats, self.color_combo]
        for _, low, high in self.speed_rows:
            controls += [low, high]
        return controls

    def reset(self) -> None:
        self.set_ready(False)
        self.canvas.clear()
        self.set_status("")
