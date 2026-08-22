"""Shared constants and units for the wind-rose engine (no GUI imports)."""

# Wind speed is expressed in metres per second throughout the application.
SPEED_UNIT = "m/s"

# Compass-point names for labelling standard sector counts.
COMPASS_NAMES = {
    4: ['N', 'E', 'S', 'W'],
    8: ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'],
    16: ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
         'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'],
}

# Default stacked-bar colours (one per speed category).
DEFAULT_COLORS = ['blue', 'cyan', 'lightgreen', 'yellow', 'red', 'darkred']

# Default contiguous speed categories in m/s. Speeds below the first lower
# bound are treated as calm.
DEFAULT_SPEED_RANGES = [(2, 5), (5, 7), (7, 10), (10, 15), (15, 20), (20, 100)]

# Matplotlib colour-map names offered in the UI (besides 'Default').
COLOR_SCHEMES = ['Default', 'viridis', 'plasma', 'cividis', 'cool', 'turbo', 'RdYlBu_r']

DEFAULT_DIR_BINS = 16
DEFAULT_NUM_SPEED_CATS = 6
