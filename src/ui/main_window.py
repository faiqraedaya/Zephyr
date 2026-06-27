"""Main application window: assembles widgets and orchestrates core + canvas.

This module is intentionally thin. All data/statistics/serialization logic
lives in :mod:`src.core`; all drawing lives in :mod:`src.ui.rose_canvas`.
"""
import os
from datetime import datetime

import numpy as np
import pandas as pd
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QFileDialog, QPushButton, QSpinBox, QLabel,
                               QDateTimeEdit, QGroupBox, QMessageBox, QComboBox)
from PySide6.QtGui import QAction
from matplotlib import colormaps

from src.core import constants, data_loader, statistics, export
from src.ui.rose_canvas import RoseCanvas
from src.ui.speed_range_widget import SpeedRangeWidget
from src.ui.data_config_widget import DataConfigWidget


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Wind Rose Analyzer')
        self.setGeometry(100, 100, 1200, 800)
        self.default_colors = constants.DEFAULT_COLORS

        self.create_menu_bar()

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)

        # Data configuration group
        data_config_group = QGroupBox('Data Configuration')
        self.data_config = DataConfigWidget()
        data_config_layout = QVBoxLayout()
        data_config_layout.addWidget(self.data_config)
        data_config_group.setLayout(data_config_layout)
        control_layout.addWidget(data_config_group)

        # Direction bins control
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel('Direction Bins:'))
        self.dir_bins = QSpinBox()
        self.dir_bins.setRange(4, 36)
        self.dir_bins.setValue(constants.DEFAULT_DIR_BINS)
        dir_layout.addWidget(self.dir_bins)
        control_layout.addLayout(dir_layout)

        # Number of speed categories control
        speed_cat_layout = QHBoxLayout()
        speed_cat_layout.addWidget(QLabel('Number of Speed Categories:'))
        self.num_speed_cats = QSpinBox()
        self.num_speed_cats.setRange(2, 10)
        self.num_speed_cats.setValue(constants.DEFAULT_NUM_SPEED_CATS)
        self.num_speed_cats.valueChanged.connect(self.update_speed_categories)
        speed_cat_layout.addWidget(self.num_speed_cats)
        control_layout.addLayout(speed_cat_layout)

        # Wind speed categories group
        self.speed_group = QGroupBox('Wind Speed Categories (m/s)')
        self.speed_layout = QVBoxLayout()
        self.speed_group.setLayout(self.speed_layout)
        control_layout.addWidget(self.speed_group)
        self.speed_ranges = []
        self.setup_default_ranges()

        # Colour scheme selector
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel('Colour Scheme:'))
        self.color_combo = QComboBox()
        self.color_combo.addItems(constants.COLOR_SCHEMES)
        self.color_combo.currentTextChanged.connect(self.on_color_changed)
        color_layout.addWidget(self.color_combo)
        control_layout.addLayout(color_layout)

        # Date range selection group
        date_group = QGroupBox('Date Range')
        date_layout = QVBoxLayout()
        self.start_date = QDateTimeEdit()
        self.end_date = QDateTimeEdit()
        self.start_date.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_date.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        date_layout.addWidget(QLabel('Start:'))
        date_layout.addWidget(self.start_date)
        date_layout.addWidget(QLabel('End:'))
        date_layout.addWidget(self.end_date)
        date_group.setLayout(date_layout)
        control_layout.addWidget(date_group)

        # Update button
        self.update_button = QPushButton('Update Wind Rose')
        self.update_button.clicked.connect(self.update_wind_rose)
        control_layout.addWidget(self.update_button)
        control_layout.addStretch(1)

        layout.addWidget(control_panel, stretch=1)
        self.canvas = RoseCanvas()
        layout.addWidget(self.canvas, stretch=3)

        self.data = None
        self.raw_data = None
        self.current_filename = "Unknown File"
        # Cache of the last computed result so exports don't recompute needlessly
        self._cache_sig = None
        self._cache = None

    # ------------------------------------------------------------------
    # Menu
    # ------------------------------------------------------------------
    def create_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu('File')
        new_action = QAction('New', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        open_action = QAction('Open Excel File', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.load_excel)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        exit_action = QAction('Exit', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        export_menu = menubar.addMenu('Export')
        export_image_action = QAction('Export Wind Rose Image', self)
        export_image_action.triggered.connect(self.export_image)
        export_menu.addAction(export_image_action)
        export_table_action = QAction('Export Wind Rose Table (Excel)', self)
        export_table_action.triggered.connect(self.export_table)
        export_menu.addAction(export_table_action)
        export_csv_action = QAction('Export Wind Rose Table (CSV)', self)
        export_csv_action.triggered.connect(self.export_csv)
        export_menu.addAction(export_csv_action)
        export_xml_action = QAction('Export Wind Rose XML', self)
        export_xml_action.triggered.connect(self.export_XML)
        export_menu.addAction(export_xml_action)

        help_menu = menubar.addMenu('Help')
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        help_action = QAction('Help', self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)

    def new_file(self):
        self.raw_data = None
        self.data = None
        self.current_filename = "Unknown File"
        self._cache_sig = None
        self._cache = None
        self.canvas.clear()
        current_date = datetime.now()
        self.start_date.setDateTime(current_date)
        self.end_date.setDateTime(current_date)

    def show_about(self):
        QMessageBox.about(self, "About Wind Rose Generator",
                          "Wind Rose Generator\n\n"
                          "Simple tool for generating wind roses.\n"
                          "Version 1.0\n\n"
                          "© Faiq Raedaya 2025")

    def show_help(self):
        help_text = """
        <h3>Wind Rose Generator Help</h3>

        <p><b>Loading Data:</b><br>
        - Use File > Open Excel File to load your wind data<br>
        - Ensure your Excel file has columns for date/time, wind speed, and wind direction</p>

        <p><b>Configuring the Display:</b><br>
        - Adjust the number of direction bins (4-36)<br>
        - Set the number of speed categories (2-10)<br>
        - Configure speed ranges for each category (boundaries must increase)</p>

        <p><b>Exporting Results:</b><br>
        - Export the wind rose as an image (PNG/JPEG)<br>
        - Export the frequency table as Excel or CSV<br>
        - Export the data in XML format</p>

        <p><b>Conventions:</b><br>
        - Direction is the direction the wind blows <i>from</i>; North is at the
          top and angles increase clockwise.<br>
        - Speeds below the lowest category are treated as <i>calm</i> and reported
          separately; all frequencies are a percentage of the valid observations.</p>

        <p><b>Date Range:</b><br>
        - Select the start and end dates to analyze specific time periods (inclusive)</p>
        """
        QMessageBox.information(self, "Help", help_text)

    # ------------------------------------------------------------------
    # Speed category widgets
    # ------------------------------------------------------------------
    def setup_default_ranges(self):
        for widget in self.speed_ranges:
            widget.deleteLater()
        self.speed_ranges.clear()
        default_values = constants.DEFAULT_SPEED_RANGES
        num_categories = self.num_speed_cats.value()
        for i in range(num_categories):
            range_widget = SpeedRangeWidget()
            if i < len(default_values):
                range_widget.min_speed.setValue(default_values[i][0])
                range_widget.max_speed.setValue(default_values[i][1])
            else:
                prev_max = self.speed_ranges[-1].max_speed.value()
                range_widget.min_speed.setValue(prev_max)
                range_widget.max_speed.setValue(prev_max + 5)
            self.speed_layout.addWidget(range_widget)
            self.speed_ranges.append(range_widget)

    def update_speed_categories(self):
        self.setup_default_ranges()

    def on_color_changed(self):
        if self.data is not None:
            self.update_wind_rose()

    # ------------------------------------------------------------------
    # Data handling / computation
    # ------------------------------------------------------------------
    def process_data(self):
        if self.raw_data is None:
            return None
        try:
            return data_loader.process_data(
                self.raw_data,
                self.data_config.date_time_col.text().strip(),
                self.data_config.wind_speed_col.text().strip(),
                self.data_config.wind_dir_col.text().strip(),
                self.data_config.first_row.value(),
                self.data_config.last_row.value(),
                self.data_config.date_format.text().strip(),
            )
        except data_loader.DataError as e:
            QMessageBox.critical(self, "Data Error", str(e))
            return None
        except Exception as e:
            QMessageBox.critical(self, "Data Processing Error",
                                 f"Error processing data: {str(e)}")
            return None

    def get_speed_ranges(self):
        return [(w.min_speed.value(), w.max_speed.value()) for w in self.speed_ranges]

    def get_filtered_data(self):
        if self.data is None:
            return None
        start = self.start_date.dateTime().toPython()
        end = self.end_date.dateTime().toPython()
        mask = (self.data['Date & Time'] >= start) & (self.data['Date & Time'] <= end)
        return self.data[mask]

    def compute_result(self, refresh=False):
        """Return ``(filtered, result, edges, maxs)`` using a cache when inputs
        are unchanged. Shows a dialog and returns ``None`` on any problem."""
        if refresh:
            self.data = self.process_data()
            self._cache_sig = None
        if self.data is None:
            return None
        filtered = self.get_filtered_data()
        if filtered is None or filtered.empty:
            QMessageBox.warning(self, "No Data",
                                "No data falls within the selected date range.")
            return None
        ranges = self.get_speed_ranges()
        edges = statistics.speed_edges_from_ranges(ranges)
        if edges is None:
            QMessageBox.warning(self, "Invalid Speed Ranges",
                                "Speed category boundaries must be strictly "
                                "increasing (each 'From' should match the previous "
                                "'To').")
            return None
        maxs = [r[1] for r in ranges]
        sig = (id(self.data), self.start_date.dateTime().toPython(),
               self.end_date.dateTime().toPython(), self.dir_bins.value(),
               tuple(edges), len(filtered))
        if self._cache_sig != sig:
            result = statistics.compute_wind_rose(
                filtered['Wind Direction'].to_numpy(float),
                filtered['Wind Speed'].to_numpy(float),
                self.dir_bins.value(), edges)
            self._cache_sig = sig
            self._cache = (filtered, result, edges, maxs)
        return self._cache

    def _category_colors(self, n_cats):
        name = self.color_combo.currentText()
        if name == 'Default':
            if n_cats <= len(self.default_colors):
                return self.default_colors[:n_cats]
            cmap = colormaps['turbo']
            return [cmap(x) for x in np.linspace(0, 1, n_cats)]
        cmap = colormaps[name]
        return [cmap(x) for x in np.linspace(0.15, 0.95, n_cats)]

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def update_wind_rose(self):
        bundle = self.compute_result(refresh=True)
        if bundle is None:
            return
        filtered, result, edges, maxs = bundle
        speeds = filtered['Wind Speed'].to_numpy(float)
        meta = {
            'filename': os.path.basename(self.current_filename.replace('\\', '/')),
            'start_str': self.start_date.dateTime().toString('yyyy-MM-dd HH:mm'),
            'end_str': self.end_date.dateTime().toString('yyyy-MM-dd HH:mm'),
            'avg_speed': float(np.nanmean(speeds)) if speeds.size else float('nan'),
        }
        colors = self._category_colors(result['counts'].shape[0])
        self.canvas.plot(result, edges, colors, meta)

    def load_excel(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Excel file", "",
            "Excel Files (*.xlsx *.xls);;All Files (*)")
        if filename:
            try:
                self.raw_data = data_loader.load_excel(filename)
                self.current_filename = filename
                self._cache_sig = None
                self.data = self.process_data()
                if self.data is not None:
                    self.start_date.setDateTime(self.data['Date & Time'].min())
                    self.end_date.setDateTime(self.data['Date & Time'].max())
                    self.update_wind_rose()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error loading Excel file: {str(e)}")

    # ------------------------------------------------------------------
    # Exports
    # ------------------------------------------------------------------
    def create_frequency_table(self):
        bundle = self.compute_result()
        if bundle is None:
            return None
        _, result, _, _ = bundle
        return statistics.frequency_table(result)

    def export_image(self):
        if self.data is None:
            QMessageBox.information(self, "Nothing to Export",
                                   "Generate a wind rose before exporting.")
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Wind Rose Image", "",
            "PNG Files (*.png);;JPEG Files (*.jpg);;All Files (*)")
        if file_path:
            try:
                self.canvas.figure.savefig(file_path, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "Export Successful", f"Image exported to \n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Error saving image: {str(e)}")

    def export_table(self):
        freq_table = self.create_frequency_table()
        if freq_table is None:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Wind Rose Table", "", "Excel Files (*.xlsx);;All Files (*)")
        if file_path:
            try:
                freq_table.to_excel(file_path)
                QMessageBox.information(self, "Export Successful", f"Table exported to \n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Error saving table: {str(e)}")

    def export_csv(self):
        freq_table = self.create_frequency_table()
        if freq_table is None:
            return
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Wind Rose Table", "", "CSV Files (*.csv);;All Files (*)")
        if file_path:
            try:
                freq_table.to_csv(file_path)
                QMessageBox.information(self, "Export Successful", f"Table exported to \n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Error saving CSV: {str(e)}")

    def export_XML(self):
        bundle = self.compute_result()
        if bundle is None:
            return
        _, result, edges, maxs = bundle
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Wind Rose XML", "", "XML Files (*.xml);;All Files (*)")
        if file_path:
            try:
                tree = export.wind_rose_to_xml_tree(result, maxs)
                tree.write(file_path, xml_declaration=True, encoding='utf-8', method="xml")
                QMessageBox.information(self, "Export Successful", f"XML exported to \n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Error saving XML: {str(e)}")
