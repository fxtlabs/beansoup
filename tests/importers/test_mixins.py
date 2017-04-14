"""Unit tests for beansoup.importers.mixins module."""

from os import path
import tempfile

from beancount import loader
from beancount.ingest import cache
from beancount.parser import cmptest

from beansoup.importers import mixins
from beansoup.utils import testing


class Importer(mixins.FilterChain, testing.ConstImporter):
    pass


class TestFilterChainMixin(cmptest.TestCase):

    @loader.load_doc(expect_errors=True)
    def test_mixin(self, entries, errors, _):
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
        def filter_last_two(entries):
            return entries[-2:]

        file = cache.get_file(path.join(tempfile.gettempdir(), 'test'))

        # Running with no filters should return the extracted entries unchanged
        importer = Importer(entries, 'Assets:US:BofA:Checking', filters=[])
        extracted_entries = importer.extract(file)
        self.assertEqualEntries(extracted_entries, entries)

        # Run with a filter that should pass only the last two entries
        importer = Importer(entries, 'Assets:US:BofA:Checking',
                            filters=[filter_last_two])
        extracted_entries = importer.extract(file)
        self.assertEqualEntries(extracted_entries, entries[-2:])
