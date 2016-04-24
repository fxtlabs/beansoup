"""Unit tests for beansoup.utils.dates module."""

import datetime
from dateutil import parser
import pytest

from beansoup.utils import dates


month_number_data = [
    ('january', 1),
    ('FEBRUARY', 2),
    ('March', 3),
    ('aPRIL', 4),
    ('mAy', 5),
    ('jun', 6),
    ('Jul', 7),
    ('AUG', 8),
    ('09', 9),
    ('10', 10),
    ('nov', 11),
    ('12', 12),
    (None, None),
    (3, None),
    ([4], None),
    ('', None),
    ('janua', None),
]

@pytest.mark.parametrize('s,expected', month_number_data)
def test_month_number(s, expected):
    assert dates.month_number(s) == expected


add_biz_days_data = [
    # 2016-01-05 falls on a Tuesday
    ('2016-01-05', 0, '2016-01-05'),
    ('2016-01-05', 1, '2016-01-06'),
    ('2016-01-05', 2, '2016-01-07'),
    ('2016-01-05', 3, '2016-01-08'),
    ('2016-01-05', 4, '2016-01-11'),
    ('2016-01-05', 5, '2016-01-12'),
    ('2016-01-05', 6, '2016-01-13'),
    ('2016-01-05', 7, '2016-01-14'),
    ('2016-01-05', 8, '2016-01-15'),
    ('2016-01-05', 9, '2016-01-18'),
    ('2016-01-05', 10, '2016-01-19'),
    # 2016-02-06 falls on a Saturday
    ('2016-02-06', 0, '2016-02-08'),
    ('2016-02-06', 1, '2016-02-09'),
    ('2016-02-06', 2, '2016-02-10'),
    ('2016-02-06', 3, '2016-02-11'),
    ('2016-02-06', 4, '2016-02-12'),
    ('2016-02-06', 5, '2016-02-15'),
    ('2016-02-06', 6, '2016-02-16'),
    ('2016-02-06', 7, '2016-02-17'),
    ('2016-02-06', 8, '2016-02-18'),
    ('2016-02-06', 9, '2016-02-19'),
    ('2016-02-06', 10, '2016-02-22'),
    # 2016-02-07 falls on a Sunday
    ('2016-02-07', 0, '2016-02-08'),
    ('2016-02-07', 1, '2016-02-09'),
    ('2016-02-07', 2, '2016-02-10'),
    ('2016-02-07', 3, '2016-02-11'),
    ('2016-02-07', 4, '2016-02-12'),
    ('2016-02-07', 5, '2016-02-15'),
    ('2016-02-07', 6, '2016-02-16'),
    ('2016-02-07', 7, '2016-02-17'),
    ('2016-02-07', 8, '2016-02-18'),
    ('2016-02-07', 9, '2016-02-19'),
    ('2016-02-07', 10, '2016-02-22'),
]

@pytest.mark.parametrize('date_str,days,expected_str', add_biz_days_data)
def test_add_biz_days(date_str, days, expected_str):
    date = parser.parse(date_str).date()
    expected = parser.parse(expected_str).date()
    assert dates.add_biz_days(date, days) == expected


def test_add_biz_days_neg():
    with pytest.raises(AssertionError):
        dates.add_biz_days(datetime.date.today(), -1)
