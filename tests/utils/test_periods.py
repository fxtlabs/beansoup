"""Unit tests for beansoup.utils.periods module."""

import datetime
from dateutil import parser
import itertools
import pytest

from beansoup.utils import periods


bounds_data = [
    ('2016-01-01', 1, '2016-01-01', '2016-01-31'),
    ('2016-01-02', 1, '2016-01-01', '2016-01-31'),
    ('2016-01-31', 1, '2016-01-01', '2016-01-31'),
    ('2016-01-01', 15, '2015-12-15', '2016-01-14'),
    ('2016-01-14', 15, '2015-12-15', '2016-01-14'),
    ('2016-01-15', 15, '2016-01-15', '2016-02-14'),
    ('2016-01-16', 15, '2016-01-15', '2016-02-14'),
    ('2015-12-14', 15, '2015-11-15', '2015-12-14'),
    ('2015-12-15', 15, '2015-12-15', '2016-01-14'),
    ('2015-12-16', 15, '2015-12-15', '2016-01-14'),
]

@pytest.mark.parametrize('date_str,first_day,lo_expected_str,hi_expected_str',
                         bounds_data)
def test_bounds(date_str, first_day, lo_expected_str, hi_expected_str):
    date = parser.parse(date_str).date()
    lo_expected = parser.parse(lo_expected_str).date()
    hi_expected = parser.parse(hi_expected_str).date()
    assert periods.enclose_date(date, first_day) == (lo_expected, hi_expected)
    assert periods.greatest_start(date, first_day) == lo_expected
    assert periods.lowest_end(date, first_day) == hi_expected


@pytest.mark.parametrize('first_day', [-1, 0, 29])
def test_bounds_exc(first_day):
    today = datetime.date.today()
    with pytest.raises(AssertionError):
        periods.enclose_date(today, first_day)
    with pytest.raises(AssertionError):
        periods.greatest_start(today, first_day)
    with pytest.raises(AssertionError):
        periods.lowest_end(today, first_day)


next_data = [
    ('2016-01-01', '2016-02-01'),
    ('2016-02-28', '2016-03-28'),
    ('2016-02-29', '2016-03-29'),
    ('2016-12-15', '2017-01-15'),
    ('2015-02-28', '2015-03-28'),
]

@pytest.mark.parametrize('date_str,expected_str', next_data)
def test_next(date_str, expected_str):
    date = parser.parse(date_str).date()
    expected = parser.parse(expected_str).date()
    assert periods.next(date) == expected


@pytest.mark.parametrize('expected_str,date_str', next_data)
def test_prev(date_str,expected_str):
    date = parser.parse(date_str).date()
    expected = parser.parse(expected_str).date()
    assert periods.prev(date) == expected


count_data = [date for date, _ in next_data]

@pytest.mark.parametrize('date_str', count_data)
def test_count_forward(date_str):
    start_date = parser.parse(date_str).date()
    n = 10
    for i, date in enumerate(itertools.islice(
            periods.count(start_date, reverse=False),
            0, n)):
        if i > 0:
            assert date == periods.next(prev_date)
        else:
            assert date == start_date
        prev_date = date


@pytest.mark.parametrize('date_str', count_data)
def test_count_backward(date_str):
    start_date = parser.parse(date_str).date()
    n = 10
    for i, date in enumerate(itertools.islice(
            periods.count(start_date, reverse=True),
            0, n)):
        if i > 0:
            assert date == periods.prev(next_date)
        else:
            assert date == start_date
        next_date = date
