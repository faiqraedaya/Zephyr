"""Matplotlib canvas widget and the wind-rose plotting code."""
import os
# Ensure matplotlib binds to PySide6 (not PyQt5) for its Qt backend.
os.environ.setdefault("QT_API", "pyside6")

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from wind_rose_generator.core.statistics import speed_labels, compass_name


class RoseCanvas(FigureCanvasQTAgg):
    """A Qt canvas that renders a stacked polar wind rose plus an info panel."""

    def __init__(self, parent=None):
        self.figure = Figure(figsize=(8, 8))
        super().__init__(self.figure)
        self.setParent(parent)

    def clear(self):
        self.figure.clear()
        self.draw()

    def plot(self, result, edges, colors, meta):
        """Render ``result`` onto the figure.

        ``colors`` is one colour per speed category; ``meta`` carries the
        presentation strings (filename, date range, average speed).
        """
        fig = self.figure
        fig.clear()
        gs = fig.add_gridspec(2, 1, height_ratios=[4, 1])
        ax = fig.add_subplot(gs[0], projection='polar')

        centers_rad = np.radians(result['sector_centers'])
        width = np.radians(360.0 / result['n_sectors'])
        labels = speed_labels(edges)
        bottom = np.zeros(result['n_sectors'])
        for i, label in enumerate(labels):
            heights = result['freq'][i]
            ax.bar(centers_rad, heights, width=width, bottom=bottom,
                   label=f'{label} m/s', color=colors[i],
                   edgecolor='black', linewidth=0.3)
            bottom += heights

        ax.set_theta_direction(-1)
        ax.set_theta_zero_location('N')
        ax.set_title('Wind Rose Diagram')
        ax.legend(bbox_to_anchor=(1.2, 0.5), loc='center left', title='Wind Speed')

        if result['sector_freq'].any():
            prevailing = result['sector_centers'][np.argmax(result['sector_freq'])]
            prevailing_str = f"{prevailing:.1f}° ({compass_name(prevailing)})"
        else:
            prevailing_str = "n/a"

        ax_text = fig.add_subplot(gs[1])
        ax_text.axis('off')
        info_text = (
            f"Data Source: {meta['filename']}\n"
            f"Date Range: {meta['start_str']} to {meta['end_str']}\n"
            f"Observations: {result['total_valid']}"
            + (f" ({result['n_excluded']} excluded)" if result['n_excluded'] else "")
            + "\n"
            f"Prevailing Wind Direction: {prevailing_str}\n"
            f"Average Wind Speed: {meta['avg_speed']:.1f} m/s\n"
            f"Calm (< {edges[0]:g} m/s): {result['calm_freq']:.1f}%\n"
        )
        ax_text.text(0.05, 0.95, info_text,
                     transform=ax_text.transAxes,
                     verticalalignment='top',
                     fontfamily='monospace')
        fig.tight_layout()
        self.draw()
