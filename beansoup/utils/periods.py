"""Utilities to work with monthly billing periods."""

import calendar
import datetime
import itertools


MONTHS = dict((name.lower(), i) for i, name in itertools.chain(
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
    return MONTHS.get(month.lower()) if isinstance(month, str) else None


def enclose_date(date, first_day=1):
    """Compute the monthly period containing the given date.

    Args:
      date: A datetime.date object.
      first_day: The first day of the monthly cycle. It must be an int
        in the interval [1,28].
    Returns:
      A pair of datetime.date objects; the start and end dates of the
      monthly period containing the given date.
    """
    assert 0 < first_day < 29, "Invalid 'first_day' value {}: first day of monthly cycle must be in [1,28]".format(first_day)

    if date.day >= first_day:
        year, month = date.year, date.month
    elif date.month > 1:
        year, month = date.year, date.month - 1
    else:
        year, month = date.year - 1, 12
    _, length = calendar.monthrange(year, month)
    start = datetime.date(year, month, first_day)
    end = start + datetime.timedelta(days=length-1)
    return (start, end)
