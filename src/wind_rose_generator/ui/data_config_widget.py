from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit, QSpinBox, QLabel

class DataConfigWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)
        
        # Column selection
        self.date_time_col = QLineEdit("Date & Time")
        self.wind_speed_col = QLineEdit("Wind Speed")
        self.wind_dir_col = QLineEdit("Wind Direction")
        
        # Row range selection
        self.first_row = QSpinBox()
        self.first_row.setRange(0, 1000000)
        self.first_row.setValue(0)
        self.last_row = QSpinBox()
        self.last_row.setRange(0, 1000000)
        self.last_row.setValue(0)
        self.last_row.setSpecialValueText("End")
        
        # Date format
        self.date_format = QLineEdit("yyyy-MM-dd HH:mm:ss")
        self.date_format_help = QLabel("Examples: yyyy-MM-dd HH:mm:ss, MM/dd/yyyy HH:mm, yyyyMMdd:HHmmss")
        self.date_format_help.setWordWrap(True)
        
        # Add widgets to layout
        layout.addRow("Date && Time Column:", self.date_time_col)
        layout.addRow("Wind Speed Column:", self.wind_speed_col)
        layout.addRow("Wind Direction Column:", self.wind_dir_col)
        layout.addRow("First Data Row:", self.first_row)
        layout.addRow("Last Data Row:", self.last_row)
        layout.addRow("Date Format:", self.date_format)
        layout.addRow("", self.date_format_help) 