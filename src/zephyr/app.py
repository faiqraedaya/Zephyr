"""Application entry point: one QApplication, one theme, one window."""
import os
import sys

# Ensure matplotlib binds to PySide6 (not PyQt5) for its Qt backend.
os.environ.setdefault("QT_API", "pyside6")

from PySide6.QtWidgets import QApplication

from zephyr.gui.icons import app_icon
from zephyr.gui.main_window import MainWindow
from zephyr.gui.theme import apply_mpl_theme, apply_theme


def main() -> int:
    # Without its own AppUserModelID, Windows groups the window under
    # python.exe and shows Python's icon on the taskbar instead of ours.
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "FaiqRaedaya.Zephyr")

    app = QApplication(sys.argv)
    app.setOrganizationName("Faiq Raedaya")
    app.setApplicationName("Zephyr")
    app.setApplicationVersion("2.0.0")
    app.setWindowIcon(app_icon())

    apply_theme(app)        # the only styling call in the application
    apply_mpl_theme()       # the embedded figures match the window

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
