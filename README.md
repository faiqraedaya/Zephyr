# Wind Rose Generator

## Overview
A Python desktop application for generating highly-customizable wind rose diagrams
from meteorological datasets stored in Excel.

## Features
- Interactive GUI built with **PySide6**
- Load and process wind data from Excel files, with configurable column mapping,
  row range, and date format
- Robust data handling: non-numeric values are coerced and excluded (and reported),
  bad dates are dropped, and missing columns are reported instead of crashing
- Customizable wind direction bins (4–36 sectors) and wind speed categories (2–10 ranges)
- Correct meteorological conventions: direction is the direction the wind blows
  *from*, North is at the top, angles increase clockwise, and the North sector
  spans across 0°/360°
- Separate **calm** accounting (low-speed, undefined-direction observations) so all
  frequencies sum to 100%
- Selectable colour schemes and inclusive date-range filtering
- Real-time wind rose visualization with a summary panel (prevailing direction,
  average speed, calm %, observation counts)
- Export the wind rose image (PNG/JPEG), the frequency table (Excel or CSV), and an
  XML data format

## Installation
```bash
git clone https://github.com/faiqraedaya/Wind-Rose-Generator
cd Wind-Rose-Generator
uv sync
```

## Usage
1. Run the application:
   ```bash
   uv run main.py
   ```

2. Load your wind data:
   - Use **File → Open Excel File** to select your data file
   - Configure the data columns (date/time, wind speed in m/s, wind direction in degrees)
   - Set the appropriate date format (e.g. `yyyy-MM-dd HH:mm:ss`)

3. Customize the visualization:
   - Adjust the number of direction bins and speed categories
   - Configure the speed ranges (boundaries must be strictly increasing; speeds
     below the lowest category are treated as calm)
   - Choose a colour scheme and the date range

4. Generate and export:
   - Click **Update Wind Rose** to refresh the visualization
   - Use the **Export** menu to save the image, frequency table (Excel/CSV), or XML

## License
[MIT](LICENSE)
