from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QDoubleSpinBox

class SpeedRangeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.min_speed = QDoubleSpinBox()
        self.max_speed = QDoubleSpinBox()
        self.min_speed.setRange(0, 100)
        self.max_speed.setRange(0, 100)
        
        layout.addWidget(QLabel('From:'))
        layout.addWidget(self.min_speed)
        layout.addWidget(QLabel('To:'))
        layout.addWidget(self.max_speed) 