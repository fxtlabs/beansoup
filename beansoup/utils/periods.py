"""Utilities to work with monthly billing periods."""

import calendar
import datetime


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
    start = greatest_start(date, first_day=first_day)
    _, length = calendar.monthrange(start.year, start.month)
    return start, start + datetime.timedelta(days=length-1)


def greatest_start(date, first_day=1):
    """Compute the starting date of the monthly period containing the given date.

    More formally, it computes the greatest start date of the monthly cycle based on
    first_day that is less than or equal to the given date.

    Args:
      date: A datetime.date object.
      first_day: The first day of the monthly cycle. It must be an int
        in the interval [1,28].
    Returns:
      The starting date of the monthly period containing the given date as
      a datetime.date object.
    """
    assert 0 < first_day < 29, "Invalid 'first_day' value {}: first day of monthly cycle must be in [1,28]".format(first_day)

    if date.day >= first_day:
        year, month = date.year, date.month
    elif date.month > 1:
        year, month = date.year, date.month - 1
    else:
        year, month = date.year - 1, 12
    return datetime.date(year, month, first_day)

    
def lowest_end(date, first_day=1):
    """Compute the ending date of the monthly period containing the given date.

    More formally, it computes the lowest end date of the monthly cycle based on
    first_day that is greater than or equal to the given date.

    Args:
      date: A datetime.date object.
      first_day: The first day of the monthly cycle. It must be an int
        in the interval [1,28].
    Returns:
      The ending date of the monthly period containing the given date as
      a datetime.date object.
    """
    start = greatest_start(date, first_day=first_day)
    _, length = calendar.monthrange(start.year, start.month)
    return start + datetime.timedelta(days=length-1)

    
def next(date):
    """Add one month to the given date.

    Note that if the given date falls on a day of the month greater than the number of
    days in the following month, the result will not have the same day of the month as
    the input. For example:
      next(datetime.date(2015, 1, 30)) == datetime.date(2015, 3, 2)

    Args:
      date: A datetime.date object.
    Returns:
      A datetime.date object whose value is one month later than the given date.
    """
    _, length = calendar.monthrange(date.year, date.month)
    return date + datetime.timedelta(days=length)


def prev(date):
    """Subtract one month from the given date.

    Note that if the given date falls on a day of the month greater than the number of
    days in the following month, the result will not have the same day of the month as
    the input. For example:
      prev(datetime.date(2015, 3, 30)) == datetime.date(2015, 3, 2)

    Args:
      date: A datetime.date object.
    Returns:
      A datetime.date object whose value is one month earlier than the given date.
    """
    if date.month > 1:
        year, month = date.year, date.month - 1
    else:
        year, month = date.year - 1, 12
    _, length = calendar.monthrange(year, month)
    return date - datetime.timedelta(days=length)


def count(date, reverse=False):
    """Make and iterator that returns monthly-spaced dates.

    Args:
      date: A datetime.date object; the starting date.
      reverse: A boolean value; if True, the iterator will go back in time.
    Returns:
      An iterator.
    """
    while True:
        yield date
        date = prev(date) if reverse else next(date)
