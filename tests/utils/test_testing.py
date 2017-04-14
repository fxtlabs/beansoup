"""Unit tests for beansoup.utils.testing module."""

import datetime
from os import path
import tempfile
import unittest

from beancount import loader
from beancount.ingest import cache
from beancount.parser import cmptest

from beansoup.utils import testing


class TestDocfileDecorator(unittest.TestCase):

    @testing.docfile(mode='w', suffix='.txt')
    def test_decorator(self, filename):
        """25341344-AFEE-2CB4-C88B-72EEAFAD5ACA"""
        with open(filename) as f:
            content = f.read()
            assert content == "25341344-AFEE-2CB4-C88B-72EEAFAD5ACA"
        _, ext = path.splitext(filename)
        assert ext == '.txt'


class TestConstImporter(cmptest.TestCase):

    @loader.load_doc(expect_errors=True)
    def test_importer(self, entries, errors, _):
        """
        2014-01-01 open Assets:US:BofA:Checking                   USD

        2014-05-19 * "Verizon Wireless" ""
          Assets:US:BofA:Checking                          -44.34 USD
        
        2014-05-23 * "Wine-Tarner Cable" ""
          Assets:US:BofA:Checking                          -80.17 USD
        
        2014-06-04 * "BANK FEES" "Monthly bank fee"
          Assets:US:BofA:Checking                           -4.00 USD
        
        2014-06-04 * "RiverBank Properties" "Paying the rent"
          Assets:US:BofA:Checking                        -2400.00 USD
        
        2014-06-08 * "EDISON POWER" ""
          Assets:US:BofA:Checking                          -65.00 USD
        """
        account = 'Assets:US:BofA:Checking'
        file = cache.get_file(path.join(tempfile.gettempdir(), 'test'))
        importer = testing.ConstImporter(entries, account)

        assert importer.file_account(file) == account
        assert importer.file_name(file) == None
        assert importer.identify(file)
        assert importer.file_date(file) == datetime.date(2014, 6, 8)

        extracted_entries = importer.extract(file)
        self.assertEqualEntries(extracted_entries, entries)
