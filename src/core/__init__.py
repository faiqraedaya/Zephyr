"""GUI-independent core: data loading, statistics and serialization.

This package never imports any GUI toolkit, so it can be imported and tested
on its own with a synthetic DataFrame.
"""
from src.core import constants
from src.core.data_loader import DataError, load_excel, process_data, qt_to_strftime
from src.core.statistics import (
    assign_sectors,
    compass_name,
    compute_wind_rose,
    frequency_table,
    sector_centers,
    sector_labels,
    speed_edges_from_ranges,
    speed_labels,
)
from src.core.export import wind_rose_to_xml_tree

__all__ = [
    "constants",
    "DataError",
    "load_excel",
    "process_data",
    "qt_to_strftime",
    "assign_sectors",
    "compass_name",
    "compute_wind_rose",
    "frequency_table",
    "sector_centers",
    "sector_labels",
    "speed_edges_from_ranges",
    "speed_labels",
    "wind_rose_to_xml_tree",
]
