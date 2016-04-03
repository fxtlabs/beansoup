"""Utilities to work with monthly billing periods."""

import calendar
import itertools


months = dict((name.lower(), i) for i, name in itertools.chain(
    enumerate(calendar.month_abbr[1:], start=1),
    enumerate(calendar.month_name[1:], start=1),
    enumerate(['{0:1d}'.format(i) for i in range(1, 13)], start=1),
    enumerate(['{0:02d}'.format(i) for i in range(1, 13)], start=1)))


def month_number(month):
    """Turns a month name into its corresponding month number.

    It recognizes full and abbreviated (three letters) English month names
    (case insensitive) as well as month number with or without a leading 0.

    Args:
      month: A string; the name of a month.
    Returns:
      An int, the number in [1,12] corresponding to the given month name,
      or None if it does not recognize the given name.
    """
    return months.get(month.lower()) if isinstance(month, str) else None
