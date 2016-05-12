"""Unit tests for beansoup.importers.filing module."""

import datetime
import pytest
from os import path
import tempfile

from beancount.ingest import cache

from beansoup.importers import filing


DATADIR = tempfile.gettempdir()


def test_basics():
    account = 'Assets:Checking'
    importer = filing.Importer(
        account, basename=None, filename_regexp='test.pdf')
    file = cache.get_file(path.join(DATADIR, 'test.pdf'))

    assert importer.name() == 'beansoup.importers.filing.Importer: "{}"'.format(account)
    assert importer.file_account(file) == account
    assert importer.file_name(file) == None
    assert importer.extract(file) == []

    account = 'Liabilities:Visa'
    importer = filing.Importer(
        account, basename='filed', filename_regexp='test.pdf')
    file = cache.get_file(path.join(DATADIR, 'test.pdf'))
    assert importer.name() == 'beansoup.importers.filing.Importer: "{}"'.format(account)
    assert importer.file_account(file) == account
    assert importer.file_name(file) == 'filed.pdf'
    assert importer.extract(file) == []


identify_data = [
    ('test-01.pdf', True),
    ('test-02.csv', True),
    ('test-03.txt', False),
    ('test-ab.pdf', False),
]

@pytest.mark.parametrize('filename,expected', identify_data)
def test_identify(filename, expected):
    importer = filing.Importer('Assets:Testing',
                               filename_regexp=r'test-\d{2}\.(pdf|csv)')
    file = cache.get_file(path.join(DATADIR, filename))
    if expected:
        assert importer.identify(file)
    else:
        assert not importer.identify(file)

        
file_date_data = [
    (1, 'test.pdf', 'no-match.pdf', None),
    (1, '^test_(?P<month>\w{3})_(?P<year>\d{4}).pdf$',
     'test_May_2016.pdf', datetime.date(2016, 5, 31)),
    (2, '^test_(?P<month>\d{2})_(?P<year>\d{4}).pdf$',
     'test_05_2016.pdf', datetime.date(2016, 5, 1)),
    (31, '^test_(?P<year>\d{4})_(?P<month>\w{3}).pdf$',
     'test_2016_may.pdf', datetime.date(2016, 5, 30)),
    (1, '^test_(?P<month>\w{3,})_(?P<day>\d{1,2})_(?P<year>\d{4}).pdf$',
     'test_April_12_2016.pdf', datetime.date(2016, 4, 12)),
    (30, '^test_(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2}).pdf$',
     'test_2016-04-12.pdf', datetime.date(2016, 4, 12)),
]

@pytest.mark.parametrize('first_day,filename_regexp,filename,expected',
                         file_date_data)
def test_file_date(first_day, filename_regexp, filename, expected):
    importer = filing.Importer('Assets:Testing',
                               first_day=first_day,
                               filename_regexp=filename_regexp)
    file = cache.get_file(path.join(DATADIR, filename))
    assert importer.file_date(file) == expected
