<img src="src/zephyr/gui/assets/zephyr.svg" alt="Zephyr icon" width="64">

# Zephyr

## Overview
*Zephyr is a desktop application that builds wind rose diagrams and frequency tables from meteorological data in Excel. It turns time series of wind speed and direction into a configurable, self-describing wind rose for reports and studies.*

## Features
- Excel import with column mapping from the workbook's own headings, a row range and a date format
- Non-numeric values and unparseable dates excluded and reported
- 4 to 36 direction sectors and 2 to 10 speed categories, validated as they are entered
- Meteorological convention: direction the wind blows from, North at the top, clockwise angles
- Calm observations counted separately, so all frequencies sum to 100 %
- Inclusive date-range filtering and a choice of sequential colour schemes
- Diagram footnote with source, period, observation counts, prevailing direction, mean speed and calm share
- Export of the diagram to PNG or JPEG and the frequency table to Excel, CSV or XML

## Install
```bash
git clone https://github.com/faiqraedaya/Zephyr
cd Zephyr
uv sync
```

## Usage
```bash
uv run zephyr
```
On the Data page, click Choose Excel file, map the date, speed (m/s) and direction (degrees) columns, and click Load data. On the Wind rose page, click Update wind rose. Use the Export menu to save the diagram or the frequency table.

## Technical details
Input is an Excel workbook read with pandas. Each row needs a date and time, a wind speed in m/s and a wind direction in degrees. Dates are parsed with the configured format, falling back to pandas inference. Speed and direction are coerced to numbers, and non-finite values are excluded and counted.

Each direction is assigned to a sector centred on its compass bearing, with the North sector spanning 0°/360°. Speeds below the first speed boundary count as calm, and the top speed category is open-ended. Frequencies are percentages of all valid observations, so the petals and the calm share together sum to 100 %. The rose is drawn with Matplotlib on a polar axis. Speed bands use a sequential colour scale, either the application's own or a Matplotlib colour map.

The diagram exports as PNG or JPEG. The frequency table (speed category against direction sector, in percent) exports as Excel or CSV. The XML export holds the calm fraction, velocity bands, sector directions and per-heading probabilities as fractions.

## License
MIT — see [LICENSE](LICENSE).
