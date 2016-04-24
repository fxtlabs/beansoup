"""Unit tests for beansoup.utils.dates module."""

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
