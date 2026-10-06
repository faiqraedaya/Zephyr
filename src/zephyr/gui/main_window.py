"""The window shell: navigation, the page stack, the menus and the status bar.

The window owns the data and orchestrates the core; the pages own their
controls and know nothing about each other. Anything that can take a moment -
reading a workbook, binning a season of observations - runs on a worker
thread with the triggering controls disabled, so the window never freezes
with no explanation.
"""
from __future__ import annotations

import os

import numpy as np
from PySide6.QtCore import QSettings, QSize
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (QFileDialog, QLabel, QMainWindow, QMessageBox,
                               QProgressBar, QStackedWidget, QWidget)
from matplotlib import colormaps
from matplotlib.colors import LinearSegmentedColormap

from zephyr.core import constants, data_loader, export, statistics
from zephyr.gui import layout as ly
from zephyr.gui.data_page import DataPage
from zephyr.gui.icons import icon
from zephyr.gui.rose_page import RosePage
from zephyr.gui.sidebar import PAGES, Sidebar, SidebarStrip
from zephyr.gui.table_page import TablePage
from zephyr.gui.theme import Tokens as T
from zephyr.gui.worker import BusyGuard, Worker

_NO_DATA = "Load a workbook on the Data page first."
_NO_ROSE = "Update the wind rose before exporting."


def _compute(data, cfg):
    """Filter, bin and count - the whole calculation, off the GUI thread."""
    mask = ((data['Date & Time'] >= cfg['start'])
            & (data['Date & Time'] <= cfg['end']))
    filtered = data[mask]
    if filtered.empty:
        raise ValueError("No observations fall inside the selected analysis "
                         "period. Widen the start and end dates.")
    edges = statistics.speed_edges_from_ranges(cfg['ranges'])
    if edges is None:
        raise ValueError("Speed category boundaries must increase from top to "
                         "bottom.")
    speeds = filtered['Wind Speed'].to_numpy(float)
    result = statistics.compute_wind_rose(
        filtered['Wind Direction'].to_numpy(float), speeds,
        cfg['n_sectors'], edges)
    if not result['total_valid']:
        raise ValueError("Every observation in this period is missing a speed "
                         "or a direction, so there is nothing to plot.")
    return {
        'result': result,
        'edges': edges,
        'maxs': [r[1] for r in cfg['ranges']],
        'avg_speed': float(np.nanmean(speeds)) if speeds.size else float('nan'),
    }


class MainWindow(QMainWindow):
    """Navigation rail, one page per destination, one status line."""

    # The narrowest arrangement that does not clip: the rail at its minimum
    # beside the Wind rose page's control column and its polar plot.
    MIN_W = Sidebar.MIN_W + T.SPLITTER_GRAB + 2 * T.MARGIN_WINDOW \
        + RosePage.CONTROLS_MIN_W + T.SPLITTER_GRAB + RosePage.CANVAS_MIN_W
    MIN_H = 620
    PAGE_ICON_SIZE = 24   # sized to sit beside the title, on the 8 px grid

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Zephyr")
        self.setMinimumSize(self.MIN_W, self.MIN_H)

        self.settings = QSettings()
        self.raw_data = None
        self.data = None
        self.current_filename = ""
        self._bundle = None
        self._worker = None
        self._retired = []      # threads awaiting Qt's finished signal

        self._build_shell()
        self._build_menus()
        self._build_status_bar()
        self._restore_settings()
        self.set_status("Choose an Excel workbook on the Data page to begin.")

    # ------------------------------------------------------------------
    # Shell
    # ------------------------------------------------------------------
    def _build_shell(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)

        self.sidebar = Sidebar()
        self.sidebar.selected.connect(self._go_to)
        self.sidebar.collapse_requested.connect(self._toggle_sidebar)
        self.sidebar_strip = SidebarStrip()
        self.sidebar_strip.expand_requested.connect(self._toggle_sidebar)
        self.sidebar_strip.hide()

        content, content_layout = ly.panel(margin=0)
        content_layout.setContentsMargins(T.MARGIN_WINDOW, T.MARGIN_WINDOW,
                                          T.MARGIN_WINDOW, T.MARGIN_WINDOW)
        content_layout.addLayout(self._content_header())

        self.data_page = DataPage()
        self.rose_page = RosePage()
        self.table_page = TablePage()
        self.data_page.browse_requested.connect(self._browse)
        self.data_page.load_requested.connect(self._load)
        self.rose_page.update_requested.connect(self._update_rose)

        self.stack = QStackedWidget()
        for page in (self.data_page, self.rose_page, self.table_page):
            self.stack.addWidget(page)
        content_layout.addWidget(self.stack, 1)

        self.splitter = ly.splitter(self.sidebar, content,
                                    sizes=[Sidebar.DEFAULT_W, 900],
                                    stretch=[0, 1])
        root = ly.hbox(central, margin=0, spacing=0)
        root.addWidget(self.sidebar_strip)
        root.addWidget(self.splitter)

    def _content_header(self):
        """One placement for the page title, driven by the navigation."""
        header = ly.hbox(spacing=T.SPACING_ROW + 4)
        self.page_icon = QLabel()
        self.page_icon.setFixedSize(self.PAGE_ICON_SIZE, self.PAGE_ICON_SIZE)
        self._set_page_icon(PAGES[0][2])
        header.addWidget(self.page_icon)

        self.page_title = ly.title(PAGES[0][1])
        header.addWidget(self.page_title)
        header.addStretch(1)
        return header

    def _set_page_icon(self, glyph: str):
        """The current page's own glyph, in title ink, beside its title."""
        size = self.PAGE_ICON_SIZE
        self.page_icon.setPixmap(icon(glyph, size=size).pixmap(
            QSize(size, size), QIcon.Normal, QIcon.On))

    def _build_status_bar(self):
        bar = self.statusBar()
        self._status_label = QLabel("")
        bar.addWidget(self._status_label, 1)
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)          # indeterminate
        self._progress.setTextVisible(False)
        self._progress.setMinimumWidth(120)
        self._progress.setMaximumWidth(120)
        self._progress.setVisible(False)
        bar.addPermanentWidget(self._progress)

    def _build_menus(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        self._action(file_menu, "New", self.new_file, QKeySequence.New)
        self._action(file_menu, "Open Excel file…", self._browse,
                     QKeySequence.Open)
        file_menu.addSeparator()
        self._action(file_menu, "Exit", self.close, QKeySequence.Quit)

        export_menu = menubar.addMenu("Export")
        self._action(export_menu, "Wind rose image…", self.export_image)
        self._action(export_menu, "Frequency table (Excel)…", self.export_table)
        self._action(export_menu, "Frequency table (CSV)…", self.export_csv)
        self._action(export_menu, "Wind rose XML…", self.export_xml)

        view_menu = menubar.addMenu("View")
        self.toggle_action = self._action(view_menu, "Hide navigation",
                                          self._toggle_sidebar, "Ctrl+B")
        view_menu.addSeparator()
        for index, (_key, label, _glyph) in enumerate(PAGES):
            self._action(view_menu, label,
                         lambda _checked=False, i=index: self._select(i),
                         f"Ctrl+{index + 1}")

        help_menu = menubar.addMenu("Help")
        self._action(help_menu, "Help", self.show_help, QKeySequence.HelpContents)
        self._action(help_menu, "About", self.show_about)

    def _action(self, menu, text, slot, shortcut=None):
        action = QAction(text, self)
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.triggered.connect(slot)
        menu.addAction(action)
        return action

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def _go_to(self, index: int):
        self.stack.setCurrentIndex(index)
        self.page_title.setText(PAGES[index][1])
        self._set_page_icon(PAGES[index][2])
        self.settings.setValue("page", index)

    def _select(self, index: int):
        self.sidebar.set_current(index)
        self._go_to(index)

    def _toggle_sidebar(self):
        showing = self.sidebar.isVisible()
        if showing:
            self._sidebar_width = self.splitter.sizes()[0] or Sidebar.DEFAULT_W
            self.sidebar.hide()
            self.sidebar_strip.show()
        else:
            self.sidebar_strip.hide()
            self.sidebar.show()
            width = getattr(self, "_sidebar_width", Sidebar.DEFAULT_W)
            self.splitter.setSizes([width, max(self.width() - width, 400)])
        self.toggle_action.setText("Show navigation" if showing
                                   else "Hide navigation")
        self.settings.setValue("sidebar_visible", not showing)

    # ------------------------------------------------------------------
    # Busy protocol - pages reach it through window(), never by reference
    # ------------------------------------------------------------------
    def set_status(self, message: str) -> None:
        self._status_label.setText(message)

    def set_busy(self, busy: bool, message: str = "") -> None:
        self._progress.setVisible(busy)
        if message:
            self.set_status(message)

    def _run(self, fn, args, guard, on_done, on_failed):
        """One background job at a time, with its controls locked while it runs.

        The thread object is held until Qt says it has finished, not until its
        result arrives: dropping the last reference inside the result slot
        destroys a QThread that has not yet returned from ``run``. Clearing
        ``_worker`` first is what lets one job start the next.
        """
        if self._worker is not None and self._worker.isRunning():
            return
        guard.start()
        worker = Worker(fn, *args)
        self._worker = worker
        self._retired.append(worker)

        def release(payload=None, callback=None):
            if self._worker is worker:
                self._worker = None
            callback(payload)

        def retire():
            if worker in self._retired:
                self._retired.remove(worker)
            worker.deleteLater()

        worker.finished.connect(retire)
        worker.done.connect(lambda payload: release(payload, on_done))
        worker.failed.connect(lambda message: release(message, on_failed))
        worker.start()

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------
    def _browse(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Excel file", "",
            "Excel files (*.xlsx *.xls);;All files (*)")
        if not filename:
            return
        guard = BusyGuard(self.data_page, self.data_page.busy_controls(),
                          f"Reading {os.path.basename(filename)}…")
        self._run(data_loader.load_excel, (filename,), guard,
                  lambda raw: self._workbook_read(guard, filename, raw),
                  lambda message: self._workbook_failed(guard, message))

    def _workbook_read(self, guard, filename, raw):
        self.raw_data = raw
        self.current_filename = filename
        self.data_page.set_path(filename)
        self.data_page.set_columns(list(raw.columns))
        self._guess_columns(list(raw.columns))
        rows, cols = raw.shape
        guard.stop(f"Read {rows:,} rows and {cols} columns from "
                   f"{os.path.basename(filename)}.")
        self.data_page.set_status(
            f"{rows:,} rows and {cols} columns found. Confirm the column "
            f"mapping below, then select Load data.", "success")

    def _workbook_failed(self, guard, message):
        guard.stop("The workbook could not be read.")
        self.data_page.set_status(f"Could not read the workbook: {message}",
                                  "error")

    def _guess_columns(self, names):
        """Pre-select the obvious headings so a first run needs no typing."""
        wanted = ((self.data_page.date_time_col, ("date", "time")),
                  (self.data_page.wind_speed_col, ("speed", "wind spd")),
                  (self.data_page.wind_dir_col, ("dir",)))
        for combo, needles in wanted:
            if combo.currentText() in [str(n) for n in names]:
                continue
            for name in names:
                if any(needle in str(name).lower() for needle in needles):
                    combo.setCurrentText(str(name))
                    break

    def _load(self):
        if self.raw_data is None:
            self.data_page.set_status("Choose an Excel workbook first.", "error")
            return
        cfg = self.data_page.config()
        guard = BusyGuard(self.data_page, self.data_page.busy_controls(),
                          "Reading the selected columns…")
        self._run(data_loader.process_data,
                  (self.raw_data, cfg['date_col'], cfg['speed_col'],
                   cfg['dir_col'], cfg['first_row'], cfg['last_row'],
                   cfg['date_format']), guard,
                  lambda frame: self._data_loaded(guard, frame),
                  lambda message: self._load_failed(guard, message))

    def _data_loaded(self, guard, frame):
        self.data = frame
        start, end = frame['Date & Time'].min(), frame['Date & Time'].max()
        self.rose_page.set_date_range(start, end)
        self.rose_page.set_ready(True)

        speeds = frame['Wind Speed']
        directions = frame['Wind Direction']
        self.data_page.set_summary([
            ["Rows loaded", f"{len(frame):,}"],
            ["First observation", str(start)],
            ["Last observation", str(end)],
            ["Speed range",
             f"{speeds.min():.1f} to {speeds.max():.1f} {constants.SPEED_UNIT}"],
            ["Missing speeds", f"{int(speeds.isna().sum()):,}"],
            ["Missing directions", f"{int(directions.isna().sum()):,}"],
        ])
        guard.stop(f"Loaded {len(frame):,} observations.")
        self.data_page.set_status(
            f"Loaded {len(frame):,} observations. Showing the wind rose.",
            "success")
        self._select(1)
        self._update_rose()

    def _load_failed(self, guard, message):
        self.data = None
        self.rose_page.set_ready(False)
        self.table_page.reset()
        guard.stop("The columns could not be read.")
        self.data_page.set_summary([])
        self.data_page.set_status(message, "error")

    # ------------------------------------------------------------------
    # The diagram
    # ------------------------------------------------------------------
    def _update_rose(self):
        if self.data is None:
            self.rose_page.set_status(_NO_DATA, "error")
            return
        cfg = self.rose_page.config()
        guard = BusyGuard(self.rose_page, self.rose_page.busy_controls(),
                          "Binning observations…")
        self._run(_compute, (self.data, cfg), guard,
                  lambda bundle: self._rose_ready(guard, bundle, cfg),
                  lambda message: self._rose_failed(guard, message))

    def _rose_ready(self, guard, bundle, cfg):
        self._bundle = bundle
        result, edges = bundle['result'], bundle['edges']
        start_str, end_str = self.rose_page.period_strings()
        meta = {
            'filename': os.path.basename(self.current_filename) or "Unsaved data",
            'start_str': start_str,
            'end_str': end_str,
            'avg_speed': bundle['avg_speed'],
        }
        # The draw stays on the GUI thread: matplotlib cannot leave it. Only
        # the binning above ran in the worker.
        self.rose_page.canvas.plot(result, edges,
                                   self._category_colors(cfg['scheme'],
                                                         result['counts'].shape[0]),
                                   meta)
        self.table_page.set_table(statistics.frequency_table(result),
                                  result['calm_freq'], float(edges[0]),
                                  result['total_valid'])
        self.rose_page.set_status("")
        excluded = (f", {result['n_excluded']:,} excluded"
                    if result['n_excluded'] else "")
        guard.stop(f"{result['total_valid']:,} observations binned into "
                   f"{result['n_sectors']} sectors{excluded}.")

    def _rose_failed(self, guard, message):
        self._bundle = None
        self.table_page.reset()
        self.rose_page.canvas.show_message(message, tone="error")
        guard.stop("The wind rose could not be drawn.")
        self.rose_page.set_status(message, "error")

    def _category_colors(self, scheme: str, n_cats: int):
        """Speed is ordered, so every scheme runs light to dark, never a cycle.

        The theme's ramp is five fixed steps; up to ten categories are asked
        for, so the steps are interpolated rather than repeated - two
        categories sharing a colour would make the diagram unreadable.
        """
        if scheme == "Default":
            ramp = LinearSegmentedColormap.from_list(
                "theme_sequential", list(T.SERIES_SEQUENTIAL))
        else:
            ramp = colormaps[scheme]
        if n_cats == 1:
            return [ramp(0.5)]
        lo, hi = (0.0, 1.0) if scheme == "Default" else (0.15, 0.95)
        return [ramp(x) for x in np.linspace(lo, hi, n_cats)]

    # ------------------------------------------------------------------
    # File menu
    # ------------------------------------------------------------------
    def new_file(self):
        self.raw_data = None
        self.data = None
        self.current_filename = ""
        self._bundle = None
        self.data_page.reset()
        self.rose_page.reset()
        self.table_page.reset()
        self._select(0)
        self.set_status("Choose an Excel workbook on the Data page to begin.")

    def show_about(self):
        QMessageBox.about(
            self, "About Zephyr",
            "<p><b>Zephyr</b></p>"
            "<p>Customisable wind rose diagrams from meteorological Excel "
            "datasets.</p>"
            "<p>Version 2.0.0<br>© Faiq Raedaya 2025</p>")

    def show_help(self):
        QMessageBox.information(self, "Help", """
        <h3>Zephyr</h3>
        <p><b>Data</b><br>
        Choose an Excel workbook, confirm which columns hold the date and
        time, the wind speed and the wind direction, then select Load data.
        Row numbers are zero-based; leave the last row at 'End of file' to
        read to the bottom.</p>

        <p><b>Wind rose</b><br>
        Set the analysis period, the number of direction sectors (4-36) and
        the speed categories (2-10), then select Update wind rose. Speed
        boundaries must increase, and speeds below the first boundary are
        counted as calm.</p>

        <p><b>Frequency table</b><br>
        The same result as numbers: each cell is the share of valid
        observations in that direction sector and speed category.</p>

        <p><b>Conventions</b><br>
        Direction is the direction the wind blows <i>from</i>. North is at the
        top and angles increase clockwise. Petal frequencies plus the calm
        share sum to 100% of the valid observations.</p>

        <p><b>Exporting</b><br>
        The Export menu saves the diagram as an image and the frequencies as
        Excel, CSV or XML.</p>
        """)

    # ------------------------------------------------------------------
    # Exports - they save what is on screen, never a silent recomputation
    # ------------------------------------------------------------------
    def _ready_to_export(self) -> bool:
        if self._bundle is None:
            self.set_status(_NO_ROSE)
            self.rose_page.set_status(_NO_ROSE, "warning")
            self._select(1)
            return False
        return True

    def _save_path(self, caption: str, filters: str):
        path, _ = QFileDialog.getSaveFileName(self, caption, "", filters)
        return path

    def _write(self, path: str, writer, what: str):
        try:
            writer(path)
        except Exception as e:
            QMessageBox.critical(self, "Export failed",
                                 f"{what} could not be saved to\n{path}\n\n{e}")
            self.set_status(f"{what} was not saved.")
            return
        self.set_status(f"{what} saved to {path}")

    def export_image(self):
        if not self._ready_to_export():
            return
        path = self._save_path("Save wind rose image",
                               "PNG image (*.png);;JPEG image (*.jpg);;All files (*)")
        if path:
            self._write(path, lambda p: self.rose_page.canvas.figure.savefig(
                p, dpi=300, bbox_inches="tight"), "The wind rose image")

    def export_table(self):
        if not self._ready_to_export():
            return
        path = self._save_path("Save frequency table",
                               "Excel workbook (*.xlsx);;All files (*)")
        if path:
            table = statistics.frequency_table(self._bundle['result'])
            self._write(path, table.to_excel, "The frequency table")

    def export_csv(self):
        if not self._ready_to_export():
            return
        path = self._save_path("Save frequency table",
                               "CSV file (*.csv);;All files (*)")
        if path:
            table = statistics.frequency_table(self._bundle['result'])
            self._write(path, table.to_csv, "The frequency table")

    def export_xml(self):
        if not self._ready_to_export():
            return
        path = self._save_path("Save wind rose XML",
                               "XML file (*.xml);;All files (*)")
        if path:
            tree = export.wind_rose_to_xml_tree(self._bundle['result'],
                                                self._bundle['maxs'])
            self._write(path, lambda p: tree.write(
                p, xml_declaration=True, encoding="utf-8", method="xml"),
                "The wind rose XML")

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _restore_settings(self):
        geometry = self.settings.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        width = int(self.settings.value("sidebar_width", Sidebar.DEFAULT_W))
        self._sidebar_width = width
        self.splitter.setSizes([width, max(self.width() - width, 600)])
        page = int(self.settings.value("page", 0))
        self._select(page if 0 <= page < len(PAGES) else 0)
        visible = self.settings.value("sidebar_visible", True)
        if visible in (False, "false"):
            self._toggle_sidebar()

    def closeEvent(self, event):
        self.settings.setValue("geometry", self.saveGeometry())
        if self.sidebar.isVisible():
            self.settings.setValue("sidebar_width", self.splitter.sizes()[0])
        else:
            self.settings.setValue("sidebar_width",
                                   getattr(self, "_sidebar_width",
                                           Sidebar.DEFAULT_W))
        if self._worker is not None and self._worker.isRunning():
            self._worker.wait(2000)
        super().closeEvent(event)
