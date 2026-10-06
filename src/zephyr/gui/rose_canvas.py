"""The wind-rose figure: a Qt canvas plus the plotting code that fills it.

The canvas is a widget, so it lives in ``gui`` even though what it draws is
maths. Matplotlib does not read QSS, so every piece of chart chrome here is
taken from the ink ladder in :mod:`theme` and every font size is converted
from the px type scale to points. Only the data carries colour: the speed
categories are an *ordered* quantity, so they take the sequential ramp rather
than a categorical palette.
"""
import os
# Ensure matplotlib binds to PySide6 (not PyQt5) for its Qt backend.
os.environ.setdefault("QT_API", "pyside6")

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from zephyr.core.constants import SPEED_UNIT
from zephyr.core.statistics import compass_name, speed_labels
from zephyr.gui.theme import Tokens as T

# The eight cardinal points, labelled regardless of how many sectors the
# rose is binned into: 36 degree labels around the rim is unreadable, and a
# rose with no compass labels cannot be read at all.
_CARDINALS = (
    (0, "N"), (45, "NE"), (90, "E"), (135, "SE"),
    (180, "S"), (225, "SW"), (270, "W"), (315, "NW"),
)


class RoseCanvas(FigureCanvasQTAgg):
    """A Qt canvas that renders a stacked polar wind rose plus its footnote."""

    def __init__(self, parent=None, empty_text=""):
        self.figure = Figure(figsize=(7, 7), layout="constrained")
        super().__init__(self.figure)
        self.setParent(parent)
        self.empty_text = empty_text
        self.show_message(empty_text)

    def clear(self):
        """Return the canvas to its empty state."""
        self.show_message(self.empty_text)

    def show_message(self, text, tone="tertiary"):
        """Draw a single centred line instead of leaving a blank rectangle.

        A results area that is merely blank cannot tell the user whether
        nothing was found, something failed, or nothing has been run yet.
        """
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.axis("off")
        colour = T.ERROR if tone == "error" else T.ink_hex(T.INK_TERTIARY)
        if text:
            ax.text(0.5, 0.5, text, transform=ax.transAxes,
                    ha="center", va="center", wrap=True,
                    color=colour, fontsize=T.pt(T.FONT_CAPTION))
        self.draw_idle()

    # ------------------------------------------------------------------
    # The diagram
    # ------------------------------------------------------------------
    def plot(self, result, edges, colors, meta):
        """Render ``result`` onto the figure.

        ``colors`` is one colour per speed category, lightest first;
        ``meta`` carries the presentation strings (filename, date range,
        average speed) that identify an exported image.
        """
        fig = self.figure
        fig.clear()
        # The legend gets a cell of its own rather than being anchored
        # outside the polar axes: an anchored legend is laid out after the
        # figure is sized, and the longest speed label loses its tail.
        gs = fig.add_gridspec(2, 2, height_ratios=[7, 1.8],
                              width_ratios=[1, 0.26])
        ax = fig.add_subplot(gs[0, 0], projection="polar")
        legend_ax = fig.add_subplot(gs[0, 1])
        legend_ax.axis("off")

        centers_rad = np.radians(result["sector_centers"])
        width = np.radians(360.0 / result["n_sectors"])
        labels = speed_labels(edges)
        bottom = np.zeros(result["n_sectors"])
        for i, label in enumerate(labels):
            heights = result["freq"][i]
            ax.bar(centers_rad, heights, width=width, bottom=bottom,
                   label=label, color=colors[i],
                   edgecolor=T.ink_hex(T.SURFACE_BORDER_STRONG), linewidth=0.5)
            bottom += heights

        self._style_axes(ax, result)
        self._add_legend(legend_ax, ax, len(labels))
        self._add_footnote(fig.add_subplot(gs[1, :]), result, edges, meta)
        self.draw_idle()

    def _style_axes(self, ax, result):
        """Chart chrome to the ink ladder; compass labels; per-cent rings."""
        ax.set_theta_direction(-1)
        ax.set_theta_zero_location("N")

        ax.set_thetagrids([a for a, _ in _CARDINALS],
                          [n for _, n in _CARDINALS])
        ax.tick_params(axis="x", colors=T.ink_hex(T.INK_SECONDARY),
                       labelsize=T.pt(T.FONT_LABEL), pad=2)
        ax.tick_params(axis="y", colors=T.ink_hex(T.INK_TERTIARY),
                       labelsize=T.pt(T.FONT_CAPTION))

        # The rings are frequencies, so they are labelled with their unit -
        # a bare number here would not say what it counts.
        ax.yaxis.set_major_formatter(lambda v, _pos: f"{v:g}%")
        # Park the radial labels over the emptiest sector so they never sit
        # on top of a petal.
        sector_freq = result["sector_freq"]
        if sector_freq.size and sector_freq.any():
            quietest = result["sector_centers"][int(np.argmin(sector_freq))]
            ax.set_rlabel_position(float(quietest))

        ax.grid(True, color=T.ink_hex(T.SURFACE_BORDER_STRONG),
                linewidth=0.6, linestyle="-")
        ax.spines["polar"].set_color(T.ink_hex(T.SURFACE_BORDER_STRONG))
        ax.spines["polar"].set_linewidth(0.8)
        ax.set_facecolor(T.CANVAS)

    def _add_legend(self, legend_ax, rose_ax, series_count):
        """Two or more stacked series share the axes, so identity gets names."""
        if series_count < 2:
            return
        handles, labels = rose_ax.get_legend_handles_labels()
        legend = legend_ax.legend(
            handles, labels, loc="center left", frameon=False,
            title=f"Speed ({SPEED_UNIT})",
            labelcolor=T.ink_hex(T.INK_SECONDARY),
            fontsize=T.pt(T.FONT_CAPTION), handlelength=1.4,
            handleheight=1.0, borderpad=0, labelspacing=0.7,
            borderaxespad=0)
        legend.get_title().set_color(T.ink_hex(T.INK_TERTIARY))
        legend.get_title().set_fontsize(T.pt(T.FONT_CAPTION))
        legend.get_title().set_ha("left")

    def _add_footnote(self, ax, result, edges, meta):
        """Identify the diagram on the figure itself, so exports carry it.

        Each item is its caption stacked over its value, in three columns:
        putting the two side by side needs a measured label column, and
        without one a long period runs straight into the next item.
        """
        ax.axis("off")
        if result["sector_freq"].any():
            prevailing = result["sector_centers"][int(np.argmax(result["sector_freq"]))]
            prevailing_str = f"{prevailing:.1f}° ({compass_name(prevailing)})"
        else:
            prevailing_str = "n/a"

        observations = f"{result['total_valid']:,}"
        if result["n_excluded"]:
            observations += f" ({result['n_excluded']:,} excluded)"

        items = [
            ("Source", meta["filename"]),
            # Two lines: a period on one line is twice the width of any
            # other value here and runs into the column beside it.
            ("Period", "{}\nto {}".format(meta["start_str"], meta["end_str"])),
            ("Observations", observations),
            ("Prevailing direction", prevailing_str),
            ("Mean speed", f"{meta['avg_speed']:.1f} {SPEED_UNIT}"),
            (f"Calm (below {edges[0]:g} {SPEED_UNIT})",
             f"{result['calm_freq']:.1f}%"),
        ]
        size = T.pt(T.FONT_CAPTION)
        for index, (name, value) in enumerate(items):
            x = 0.005 + 0.345 * (index % 3)
            y = 0.90 - 0.50 * (index // 3)
            ax.text(x, y, name, transform=ax.transAxes, va="top", ha="left",
                    color=T.ink_hex(T.INK_TERTIARY), fontsize=size)
            ax.text(x, y - 0.22, value, transform=ax.transAxes, va="top",
                    ha="left", color=T.ink_hex(T.INK_PRIMARY), fontsize=size)
