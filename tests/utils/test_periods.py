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
    ('2016-01-29', '2016-02-29'),
    ('2016-01-31', '2016-02-29'),
    ('2016-02-28', '2016-03-28'),
    ('2016-02-29', '2016-03-29'),
    ('2016-12-15', '2017-01-15'),
]

@pytest.mark.parametrize('date_str,expected_str', next_data)
def test_next(date_str, expected_str):
    date = parser.parse(date_str).date()
    expected = parser.parse(expected_str).date()
    assert periods.next(date) == expected


prev_data = [
    ('2016-01-01', '2015-12-01'),
    ('2016-01-31', '2015-12-31'),
    ('2016-02-29', '2016-01-29'),
    ('2016-03-29', '2016-02-29'),
    ('2016-03-31', '2016-02-29')
]

@pytest.mark.parametrize('date_str,expected_str', prev_data)
def test_prev(date_str,expected_str):
    date = parser.parse(date_str).date()
    expected = parser.parse(expected_str).date()
    assert periods.prev(date) == expected


count_data = [
    ('2015-01-01', False, ['2015-01-01', '2015-02-01', '2015-03-01', '2015-04-01']),
    ('2015-01-15', False, ['2015-01-15', '2015-02-15', '2015-03-15', '2015-04-15']),
    ('2015-01-28', False, ['2015-01-28', '2015-02-28', '2015-03-28', '2015-04-28']),
    ('2015-01-29', False, ['2015-01-29', '2015-02-28', '2015-03-29', '2015-04-29']),
    ('2015-01-31', False, ['2015-01-31', '2015-02-28', '2015-03-31', '2015-04-30']),
    ('2015-11-30', False, ['2015-11-30', '2015-12-30', '2016-01-30', '2016-02-29']),
    ('2016-03-01', True, ['2016-03-01', '2016-02-01', '2016-01-01', '2015-12-01']),
    ('2016-03-15', True, ['2016-03-15', '2016-02-15', '2016-01-15', '2015-12-15']),
    ('2016-03-28', True, ['2016-03-28', '2016-02-28', '2016-01-28', '2015-12-28']),
    ('2016-03-29', True, ['2016-03-29', '2016-02-29', '2016-01-29', '2015-12-29']),
    ('2016-03-30', True, ['2016-03-30', '2016-02-29', '2016-01-30', '2015-12-30']),
    ('2016-03-31', True, ['2016-03-31', '2016-02-29', '2016-01-31', '2015-12-31']),
]

@pytest.mark.parametrize('date_str,reverse,expected_strs', count_data)
def test_count(date_str, reverse, expected_strs):
    start_date = parser.parse(date_str).date()
    for date, expected_str in zip(periods.count(start_date, reverse=reverse),
                                  expected_strs):
        expected = parser.parse(expected_str).date()
        assert date == expected
