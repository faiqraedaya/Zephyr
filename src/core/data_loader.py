"""Excel loading and validation -> tidy DataFrame (no GUI imports).

Fatal problems raise :class:`DataError` with a user-facing message; the UI
layer is responsible for presenting it. Recoverable issues (non-numeric or
out-of-range values) are coerced to NaN and left for the statistics engine to
exclude and report.
"""
import pandas as pd


class DataError(Exception):
    """Raised when wind data cannot be loaded or processed."""


def qt_to_strftime(fmt):
    """Convert the widget's Qt-style date tokens to strftime directives."""
    return (fmt.replace('yyyy', '%Y').replace('yy', '%y')
               .replace('MM', '%m').replace('dd', '%d')
               .replace('HH', '%H').replace('mm', '%M').replace('ss', '%S'))


def load_excel(path):
    """Read an Excel workbook into a raw DataFrame."""
    return pd.read_excel(path)


def process_data(raw, date_col, speed_col, dir_col,
                 first_row=0, last_row=0, date_format="yyyy-MM-dd HH:mm:ss"):
    """Validate and tidy a raw DataFrame into the canonical three columns.

    Returns a DataFrame with ``Date & Time``, ``Wind Speed`` and
    ``Wind Direction`` columns. ``last_row == 0`` means "to the end".
    """
    if raw is None:
        return None
    if last_row == 0:
        df = raw.iloc[first_row:].copy()
    else:
        df = raw.iloc[first_row:last_row + 1].copy()

    for col in (date_col, speed_col, dir_col):
        if col not in df.columns:
            available = ", ".join(str(c) for c in df.columns)
            raise DataError(f"Column '{col}' not found in the data.\n\n"
                            f"Available columns: {available}")
    if df.empty:
        raise DataError("The selected row range contains no rows.")

    out = pd.DataFrame(index=df.index)
    # Date/time: use as-is if already datetime, else parse with the configured
    # format and fall back to inference.
    if pd.api.types.is_datetime64_any_dtype(df[date_col]):
        out['Date & Time'] = df[date_col]
    else:
        py_fmt = qt_to_strftime(date_format)
        parsed = pd.to_datetime(df[date_col], format=py_fmt, errors='coerce')
        if parsed.isna().all():
            parsed = pd.to_datetime(df[date_col], errors='coerce')
        if parsed.isna().all():
            raise DataError(f"Could not parse any dates with format '{date_format}'.")
        out['Date & Time'] = parsed

    out['Wind Speed'] = pd.to_numeric(df[speed_col], errors='coerce')
    out['Wind Direction'] = pd.to_numeric(df[dir_col], errors='coerce')
    # Rows without a valid timestamp can't be date-filtered or plotted.
    out = out.dropna(subset=['Date & Time'])
    if out.empty:
        raise DataError("No rows with a valid date/time were found.")
    return out
