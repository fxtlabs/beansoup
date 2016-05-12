"""Unit tests for beansoup.importers.amex module."""

import datetime
import pytest
from os import path

from beancount.ingest import cache

from beansoup.importers import amex


pdf_filing_importer_data = [
    (1, 'no-match.pdf', None),
    (1, 'Statement_Jan_2016.pdf', None),
    (1, 'Statement_January 2016.pdf', None),
    (1, 'Statement_Jan 2016.pdf', datetime.date(2016, 1, 31)),
    (28, 'Statement_Feb 2016.pdf', datetime.date(2016, 2, 27)),
    (15, 'Statement_Mar 2016.pdf', datetime.date(2016, 3, 14)),
]

@pytest.mark.parametrize('first_day,filename,expected_date',
                         pdf_filing_importer_data)
def test_pdf_filing_importer(first_day, filename, expected_date):
    account = 'Liabilities:Amex'
    importer = amex.PdfFilingImporter(account,
                                      basename='amex',
                                      first_day=first_day)
    file = cache.get_file(path.join('/tmp', filename))

    assert importer.name() == 'beansoup.importers.amex.PdfFilingImporter: "{}"'.format(account)
    assert importer.file_account(file) == account
    assert importer.file_name(file) == 'amex.pdf'
    assert importer.extract(file) == []

    if expected_date:
        assert importer.identify(file)
        assert importer.file_date(file) == expected_date
    else:
        assert not importer.identify(file)
        assert not importer.file_date(file)
