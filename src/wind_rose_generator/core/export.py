"""Image-independent serialization of wind-rose results (no GUI imports).

The frequency table itself is a pandas DataFrame (see
:func:`src.core.statistics.frequency_table`), so CSV/Excel export is handled by
the DataFrame's own ``to_csv``/``to_excel``. This module provides the XML
serialization, which has a bespoke schema.
"""
import xml.etree.ElementTree as ET

from wind_rose_generator.core.statistics import frequency_table


def wind_rose_to_xml_tree(result, velocity_bands):
    """Serialise a wind-rose result to an ``ElementTree``.

    ``velocity_bands`` are the per-category upper speed bounds (as configured).
    Probabilities are written as fractions (0..1); ``Calm`` is the calm
    fraction and ``Directions`` the sector centre angles, so the document is
    self-describing and round-trippable.
    """
    table = frequency_table(result)
    root = ET.Element("Data")
    ET.SubElement(root, "Information").text = "Wind Rose Data"
    ET.SubElement(root, "Name").text = "WindRose"
    ET.SubElement(root, "Calm").text = f"{result['calm_freq'] / 100:.4f}"
    ET.SubElement(root, "Velocity_Bands").text = " ".join(str(v) for v in velocity_bands)
    ET.SubElement(root, "Directions").text = " ".join(f"{c:g}" for c in result['sector_centers'])
    headings_probabilities = ET.SubElement(root, "Headings_Probabilities")
    for column in table.columns:
        heading_prob = ET.SubElement(headings_probabilities, "Heading_Probabilities")
        heading_prob.text = " ".join(f"{val / 100:.4f}" for val in table[column])
    tree = ET.ElementTree(root)
    ET.indent(tree)
    return tree
