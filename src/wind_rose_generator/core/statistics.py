"""Direction/speed binning and frequency statistics (no GUI imports).

The functions here turn raw wind observations into a direction x speed
frequency table. They are pure and testable with a synthetic DataFrame.
"""
import numpy as np
import pandas as pd

from wind_rose_generator.core.constants import COMPASS_NAMES


def sector_centers(n_sectors):
    """Centre angle (degrees) of each direction sector, starting at North."""
    return np.arange(n_sectors) * (360.0 / n_sectors)


def sector_labels(n_sectors):
    """Human-friendly sector labels (compass names for 4/8/16, else degrees)."""
    if n_sectors in COMPASS_NAMES:
        return list(COMPASS_NAMES[n_sectors])
    return [f"{c:g}" for c in sector_centers(n_sectors)]


def compass_name(deg):
    """Nearest 16-point compass name for an angle in degrees."""
    names = COMPASS_NAMES[16]
    return names[int((deg % 360) / 22.5 + 0.5) % 16]


def assign_sectors(direction, n_sectors):
    """Map directions (deg) to sector indices, with North centred on 0/360.

    The North sector spans [-half, +half) so winds straddling 0/360 are
    counted together. Values outside [0, 360) are normalised by the modulo.
    """
    width = 360.0 / n_sectors
    idx = np.floor(((direction + width / 2.0) % 360.0) / width).astype(int)
    return np.clip(idx, 0, n_sectors - 1)


def speed_labels(speed_edges):
    """Labels for each speed category; the open-ended top bin shows ``min+``."""
    labels = []
    for i in range(len(speed_edges) - 1):
        lo, hi = speed_edges[i], speed_edges[i + 1]
        labels.append(f"{lo:g}+" if np.isinf(hi) else f"{lo:g}-{hi:g}")
    return labels


def compute_wind_rose(direction, speed, n_sectors, speed_edges):
    """Compute the direction x speed frequency table from raw observations.

    Parameters
    ----------
    direction, speed : array-like
        Wind direction (degrees, blowing *from*) and speed (m/s). May contain
        NaN; rows with a non-finite direction or speed are excluded.
    n_sectors : int
        Number of direction sectors (petals).
    speed_edges : array-like
        Monotonic speed boundaries. ``speed_edges[0]`` is the calm threshold:
        finite speeds below it are counted as *calm* (undefined direction).
        The last edge may be ``np.inf`` for an open-ended top category.

    Returns a dict of counts/frequencies (percentages of all valid rows, so
    petal frequencies plus the calm frequency sum to 100%).
    """
    direction = np.asarray(direction, dtype=float)
    speed = np.asarray(speed, dtype=float)
    speed_edges = np.asarray(speed_edges, dtype=float)

    valid = np.isfinite(direction) & np.isfinite(speed)
    n_excluded = int((~valid).sum())
    d, s = direction[valid], speed[valid]
    total = d.size
    n_cats = len(speed_edges) - 1

    counts = np.zeros((n_cats, n_sectors), dtype=int)
    calm_mask = s < speed_edges[0]
    calm_count = int(calm_mask.sum())

    non_calm = ~calm_mask
    if non_calm.any():
        sec = assign_sectors(d[non_calm], n_sectors)
        cat = np.clip(np.searchsorted(speed_edges, s[non_calm], side='right') - 1,
                      0, n_cats - 1)
        np.add.at(counts, (cat, sec), 1)

    freq = counts / total * 100.0 if total else counts.astype(float)
    return {
        'counts': counts,
        'freq': freq,
        'sector_centers': sector_centers(n_sectors),
        'sector_freq': freq.sum(axis=0),
        'calm_count': calm_count,
        'calm_freq': (calm_count / total * 100.0) if total else 0.0,
        'total_valid': total,
        'n_excluded': n_excluded,
        'n_sectors': n_sectors,
        'speed_edges': speed_edges,
    }


def speed_edges_from_ranges(ranges):
    """Build open-topped speed edges from ``(min, max)`` category tuples.

    ``edges[0]`` is the first lower bound (the calm threshold); intermediate
    edges are the category upper bounds; the top edge is ``inf``. Returns
    ``None`` if the resulting boundaries are not strictly increasing.
    """
    mins = [r[0] for r in ranges]
    maxs = [r[1] for r in ranges]
    edges = np.array([mins[0]] + maxs, dtype=float)
    if not np.all(np.diff(edges) > 0):
        return None
    edges[-1] = np.inf
    return edges


def frequency_table(result):
    """Build a tidy speed x direction percentage table from a result dict."""
    rows = speed_labels(result['speed_edges'])
    cols = sector_labels(result['n_sectors'])
    return pd.DataFrame(result['freq'],
                        index=pd.Index(rows, name='Speed (m/s)'),
                        columns=pd.Index(cols, name='Direction'))
