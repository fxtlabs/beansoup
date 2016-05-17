"""Utilities to work with monthly billing periods."""

import calendar
import datetime


def enclose_date(date, first_day=1):
    """Compute the monthly period containing the given date.

    Args:
      date (datetime.date): The date to be contained.
      first_day (int): The first day of the monthly cycle. It must fall
        in the interval [1,28].

    Returns:
      Tuple[datetime.date, datetime.date]: The start and end dates (inclusives) of the
      monthly period containing the given date.
    """
    start = greatest_start(date, first_day=first_day)
    _, length = calendar.monthrange(start.year, start.month)
    return start, start + datetime.timedelta(days=length-1)


def greatest_start(date, first_day=1):
    """Compute the starting date of the monthly period containing the given date.

    More formally, given a monthly cycle starting on `first_day` day of the month,
    it computes the greatest starting date that is less than or equal to the given
    `date`.

    Args:
      date (datetime.date): An arbitrary date.
      first_day (int): The first day of the monthly cycle. It must fall
        in the interval [1,28].

    Returns:
      datetime.date: The starting date of the monthly period containing the given date.
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

    More formally, given a monthly cycle starting on `first_day` day of the month,
    it computes the lowest ending date that is greater than or equal to the given
    `date`.  Note that the ending date is inclusive, i.e. it is included in the
    monthly period.

    Args:
      date (datetime.date): An arbitrary date.
      first_day (int): The first day of the monthly cycle. It must fall
        in the interval [1,28].

    Returns:
      datetime.date: The ending date of the monthly period containing the given date.
    """
    start = greatest_start(date, first_day=first_day)
    _, length = calendar.monthrange(start.year, start.month)
    return start + datetime.timedelta(days=length-1)


def next(date):
    """Add one month to the given date.

    Args:
      date (datetime.date): The starting date.

    Returns:
      datetime.date:  One month after the starting date unless the starting
      date falls on a day that is not in the next month; in that case, it
      returns the last day of the next month.

    Example:

      >>> import datetime
      >>> print(next(datetime.date(2016, 1, 31)))
      datetime.date(2016, 2, 29)

    """
    year, month = (date.year, date.month + 1) if date.month < 12 else (date.year + 1, 1)
    _, length = calendar.monthrange(year, month)
    day = min(length, date.day)
    return datetime.date(year, month, day)


def prev(date):
    """Subtract one month from the given date.

    Args:
      date (datetime.date): The starting date.

    Returns:
      datetime.date:  One month before the starting date unless the starting
      date falls on a day that is not in the previous month; in that case, it
      returns the last day of the previous month.

    Example:

      >>> import datetime
      >>> print(prev(datetime.date(2016, 3, 31)))
      datetime.date(2016, 2, 29)

    """
    year, month = (date.year, date.month - 1) if date.month > 1 else (date.year - 1, 12)
    _, length = calendar.monthrange(year, month)
    day = min(length, date.day)
    return datetime.date(year, month, day)


def count(date, reverse=False):
    """A generator of monthly-spaced dates.

    It enumerates monthly-spaced dates, starting at the given `date`.
    If the starting date falls on a day that is not in a given month, the date for
    that month will be the last day of that month.

    Args:
      date (datetime.date): The starting date.
      reverse (bool): If True, it generates dates in reverse chronological order.

    Yields:
      datetime.date: the next date in the sequence.

    Example:
      >>> import datetime
      >>> import itertools
      >>> start = datetime.date(2016, 1, 31)
      >>> print([date.isoformat() for date in itertools.islice(periods.count(start), 5)])
      ['2016-01-31', '2016-02-29', '2016-03-31', '2016-04-30', '2016-05-31']

    """
    preferred_day = date.day
    if reverse:
        while True:
            yield date
            year, month = (date.year, date.month - 1) if date.month > 1 else \
                          (date.year - 1, 12)
            _, length = calendar.monthrange(year, month)
            day = min(length, preferred_day)
            date = datetime.date(year, month, day)
    else:
        while True:
            yield date
            year, month = (date.year, date.month + 1) if date.month < 12 else \
                          (date.year + 1, 1)
            _, length = calendar.monthrange(year, month)
            day = min(length, preferred_day)
            date = datetime.date(year, month, day)
