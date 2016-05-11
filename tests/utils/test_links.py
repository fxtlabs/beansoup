"""Unit tests for beansoup.utils.links module."""

import itertools
import pytest
import re

from beansoup.utils import links


prefix_data = [
    ('pre', 0, ['pre-0', 'pre-1', 'pre-2', 'pre-3']),
    ('prefix', 1, ['prefix-1', 'prefix-2', 'prefix-3']),
]

@pytest.mark.parametrize('prefix,start,expected', prefix_data)
def test_prefix_count(prefix, start, expected):
    assert list(itertools.islice(links.count(prefix, start), len(expected))) == expected


def test_uuid_count():
    uuid_re = re.compile(
        r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$',
        flags=re.IGNORECASE)
    for link in itertools.islice(links.count(), 10):
        assert uuid_re.match(link)
