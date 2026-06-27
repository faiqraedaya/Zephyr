import os
import sys

# Ensure matplotlib binds to PySide6 (not PyQt5) for its Qt backend.
os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtWidgets import QApplication

from src.ui import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setApplicationName("Wind Rose Generator")
    app.setApplicationVersion("1.0.0")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
