"""PySide6 GUI layer. Depends on :mod:`zephyr.core`; the reverse
never holds. Every colour, metric and font size comes from :mod:`theme`, and
every layout from the factories in :mod:`layout`.
"""
from zephyr.gui.main_window import MainWindow

__all__ = ["MainWindow"]
