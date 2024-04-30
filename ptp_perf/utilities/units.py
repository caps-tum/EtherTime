import math
from datetime import timedelta
from typing import Union, Iterable

BITS_IN_BYTE = 8
BITS_TO_BYTE = 1 / BITS_IN_BYTE
BYTES_IN_KIBIBYTE = 1024
BYTES_IN_MIBIBYTE = 1024 * 1024
BYTES_IN_MEGABIT = 1000 * 1000 / BITS_IN_BYTE
BYTES_TO_MEGABIT = 1 / BYTES_IN_MEGABIT
BYTES_IN_MEGABYTE = 1000 * 1000
BYTES_TO_MEGABYTE = 1 / BYTES_IN_MEGABYTE
NANOSECONDS_IN_SECOND = 1000000000
NANOSECONDS_IN_MILLISECOND = 1000000
NANOSECONDS_IN_MICROSECOND = 1000
NANOSECONDS_TO_SECONDS = 1 / NANOSECONDS_IN_SECOND
NANOSECONDS_TO_MICROSECOND = 1 / NANOSECONDS_IN_MICROSECOND
MILLISECONDS_TO_NANOSECONDS = 1000000
MICROSECONDS_IN_SECOND = 1000000
MICROSECONDS_TO_SECONDS = 1 / MICROSECONDS_IN_SECOND
us = MICROSECONDS_TO_SECONDS
FRACTION_TO_PERCENT = 100
HERTZ_IN_GIGAHERTZ = 1000 * 1000 * 1000
HERTZ_TO_GIGAHERTZ = 1 / HERTZ_IN_GIGAHERTZ
MEGAHERTZ_TO_GIGAHERTZ = 1 / 1000
MEGAHERTZ_TO_HERTZ = 1000 * 1000
BYTES_TO_MIBIBYTE = 1 / BYTES_IN_MIBIBYTE


def convert_all_units(factor: Union[float, int], iterable: Iterable):
    return [value * factor for value in iterable]


def format_time_offset(value: float, unit: str = "s", places: int =  0, auto_increase_places: bool = False) -> str:
    import matplotlib.ticker
    if value is None:
        return "-"
    if value >= 60:
        unit = "m"
        value /= 60
    if value >= 60:
        unit = "h"
        value /= 60
    # Abs twice on purpose: Need positive value for log and then want to compare against positive value of exponent.
    if auto_increase_places and value != 0 and math.floor(abs(math.log10(abs(value)))) % 3 == 2:
        places += 1
    formatter = matplotlib.ticker.EngFormatter(unit=unit, places=places, usetex=False)
    return formatter.format_data(value)

def format_time_delta(value: float):
    delta = timedelta(microseconds=abs(value) * NANOSECONDS_TO_MICROSECOND)
    formatted_duration = str(delta)
    return formatted_duration if value >= 0 else f"-{formatted_duration}"

def format_relative(value: float, places: int = 1):
    return f"{value:.{places}f}x"


def format_engineering(value: float, unit: str = "") -> str:
    if value == 0:
        return f"{value}{unit}"
    log_value = math.floor(math.log10(abs(value)))
    print(log_value)
    suffix, multiplier, places = {
        0: ('', 1, 1),
        1: ('', 1, 0),
        2: ('', 1, 0),
        3: ('K', 1e-3, 0),
        4: ('K', 1e-3, 0),
        5: ('K', 1e-3, 0),
        6: ('M', 1e-6, 0),
        7: ('M', 1e-6, 0),
        8: ('M', 1e-6, 0),
        9: ('G', 1e-9, 0),
        10: ('G', 1e-9, 0),
        11: ('G', 1e-9, 0),
    }[log_value]
    return f"{value * multiplier:.{places}f}{suffix}{unit}"


def format_percentage(x: float) -> str:
    if x == 0:
        return "0%"
    percentage = x * 100
    num_additional_places = 0 if abs(percentage) >= 1 else abs(math.floor(math.log10(abs(percentage))))
    return f"{percentage:.{num_additional_places}f}%"
