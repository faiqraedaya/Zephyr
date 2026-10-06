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

# Lower bound of each default speed category, in m/s. Speeds below the first
# are treated as calm. Category counts beyond these continue in 5 m/s steps.
DEFAULT_SPEED_BOUNDS = [2, 5, 7, 10, 15, 20]
DEFAULT_BOUND_STEP = 5

# Upper bound reported for the top category. The diagram treats that category
# as open-ended; this value is only the highest band written to the XML export.
DEFAULT_TOP_BOUND = 100


def default_speed_ranges(count):
    """``(min, max)`` pairs for ``count`` contiguous speed categories.

    The open-ended category stays at the top as the count grows, so asking
    for more categories subdivides the range instead of stacking new ones
    above the reported top band.
    """
    lows = list(DEFAULT_SPEED_BOUNDS[:count])
    while len(lows) < count:
        lows.append(lows[-1] + DEFAULT_BOUND_STEP)
    top = max(DEFAULT_TOP_BOUND, lows[-1] + DEFAULT_BOUND_STEP)
    return [(lows[i], lows[i + 1] if i + 1 < count else top)
            for i in range(count)]


DEFAULT_SPEED_RANGES = default_speed_ranges(6)

# Colour schemes offered in the UI. 'Default' is the application's own
# sequential ramp from the theme; the rest are matplotlib colour maps. All
# of them are sequential: speed is an ordered quantity, never an identity.
COLOR_SCHEMES = ['Default', 'viridis', 'plasma', 'cividis', 'cool', 'turbo', 'RdYlBu_r']

DEFAULT_DIR_BINS = 16
DEFAULT_NUM_SPEED_CATS = 6
