"""Unit tests for beansoup.transactions module."""

from os import path

from beancount import loader
from beancount.parser import cmptest

from beansoup import transactions


class TestTransactionCompleter(cmptest.TestCase):

    def setUp(self):
        filename = path.join(path.dirname(__file__), 'example.beancount')
        self.existing_entries, _, _ = loader.load_file(filename)
        
    @loader.load_doc(expect_errors=True)
    def test_basics_against_asset(self, entries, errors, _):
        """
            2016-04-04 * "BANK FEES" "Monthly bank fee"
              Assets:US:BofA:Checking                           -4.00 USD
            
            2016-04-05 * "RiverBank Properties" "Paying the rent"
              Assets:US:BofA:Checking                        -2400.00 USD
            
            2016-04-08 * "EDISON POWER" ""
              Assets:US:BofA:Checking                          -65.00 USD
            
            2016-04-20 * "Verizon Wireless" ""
              Assets:US:BofA:Checking                          -72.02 USD
            
            2016-04-23 * "Wine-Tarner Cable" ""
              Assets:US:BofA:Checking                          -79.90 USD
            
            2016-04-26 balance Assets:US:BofA:Checking        3200.59 USD
            
            2016-05-04 * "BANK FEES" "Monthly bank fee"
              Assets:US:BofA:Checking                           -4.00 USD
            
            2016-05-06 * "Transfering accumulated savings to other account"
              Assets:US:BofA:Checking                           -4000 USD
        """
        self.complete_basics('Assets:US:BofA:Checking', entries, """
            2016-04-04 * "BANK FEES" "Monthly bank fee"
              Assets:US:BofA:Checking                           -4.00 USD
              Expenses:Financial:Fees                            4.00 USD
            
            2016-04-05 * "RiverBank Properties" "Paying the rent"
              Assets:US:BofA:Checking                        -2400.00 USD
              Expenses:Home:Rent                              2400.00 USD
            
            2016-04-08 * "EDISON POWER" ""
              Assets:US:BofA:Checking                          -65.00 USD
              Expenses:Home:Electricity                         65.00 USD
            
            2016-04-20 * "Verizon Wireless" ""
              Assets:US:BofA:Checking                          -72.02 USD
              Expenses:Home:Phone                               72.02 USD
            
            2016-04-23 * "Wine-Tarner Cable" ""
              Assets:US:BofA:Checking                          -79.90 USD
              Expenses:Home:Internet                            79.90 USD
            
            2016-04-26 balance Assets:US:BofA:Checking        3200.59 USD
            
            2016-05-04 * "BANK FEES" "Monthly bank fee"
              Assets:US:BofA:Checking                           -4.00 USD
              Expenses:Financial:Fees                            4.00 USD
            
            2016-05-06 * "Transfering accumulated savings to other account"
              Assets:US:BofA:Checking                           -4000 USD
              Assets:US:ETrade:Cash                              4000 USD
        """)

    @loader.load_doc(expect_errors=True)
    def test_basics_against_liability(self, entries, errors, _):
        """
            2016-05-03 * "Metro Transport Authority" "Tram tickets"
              Liabilities:US:Chase:Slate                      -120.00 USD
            
            2016-05-04 * "Corner Deli" "Buying groceries"
              Liabilities:US:Chase:Slate                       -71.88 USD
            
            2016-05-05 * "Kin Soy" "Eating out with Bill"
              Liabilities:US:Chase:Slate                       -34.35 USD
            
            2016-05-07 * "China Garden" "Eating out with Joe"
              Liabilities:US:Chase:Slate                       -51.64 USD
            
            2016-05-09 * "Kin Soy" "Eating out with Joe"
              Liabilities:US:Chase:Slate                       -29.27 USD
        """
        self.complete_basics('Liabilities:US:Chase:Slate', entries, """
            2016-05-03 * "Metro Transport Authority" "Tram tickets"
              Liabilities:US:Chase:Slate                      -120.00 USD
              Expenses:Transport:Tram                          120.00 USD
            
            2016-05-04 * "Corner Deli" "Buying groceries"
              Liabilities:US:Chase:Slate                       -71.88 USD
              Expenses:Food:Groceries                           71.88 USD
            
            2016-05-05 * "Kin Soy" "Eating out with Bill"
              Liabilities:US:Chase:Slate                       -34.35 USD
              Expenses:Food:Restaurant                          34.35 USD
            
            2016-05-07 * "China Garden" "Eating out with Joe"
              Liabilities:US:Chase:Slate                       -51.64 USD
              Expenses:Food:Restaurant                          51.64 USD
            
            2016-05-09 * "Kin Soy" "Eating out with Joe"
              Liabilities:US:Chase:Slate                       -29.27 USD
              Expenses:Food:Restaurant                          29.27 USD
        """)

    def complete_basics(self, account, entries, expected_entries):
        completer = transactions.TransactionCompleter(
            self.existing_entries, account, interpolated=True)
        completed_entries = completer(entries)
        self.assertEqualEntries(completed_entries, expected_entries)
