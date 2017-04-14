"""Unit tests for deposit_in_transit plugin."""

from beancount import loader
from beancount.parser import cmptest

from beansoup.plugins import config
from beansoup.plugins import deposit_in_transit


class TestDepositInTransit(cmptest.TestCase):

    @loader.load_doc()
    def test_plugin(self, entries, errors, _):
        """
        plugin "beansoup.plugins.deposit_in_transit" "
        --auto_open --same_day_merge --flag_pending --link_prefix=deposited"
        
        2000-01-01 open Assets:Checking
        2000-01-01 open Assets:Savings
        2000-01-01 open Liabilities:Visa
        
        2000-02-01 * "This transaction should be merged with the next"
          Assets:Savings         -500.00 USD
          Assets:DIT:Checking
        
        2000-02-01 * "This transaction should be merged with the previous"
          Assets:Checking         500.00 USD
          Assets:DIT:Savings
        
        2000-02-07 * "Visa" "This transaction should be linked to the next"
          Assets:Checking        -100.00 USD
          Liabilities:DIT:Visa
        
        2000-02-09 * "This transaction should be linked to the previous"
          Liabilities:Visa        100.00 USD
          Assets:DIT:Checking
        
        2000-03-08 * "This transaction should be tagged pending"
          Assets:Checking        -150.00 USD
          Liabilities:DIT:Visa
        
        2000-03-01 ! "The Bank" "Cannot merge because of different flags"
          Assets:Savings         -300.00 USD
          Assets:DIT:Checking
        
        2000-03-01 * "The Bank" "Cannot merge because of different flags"
          Assets:Checking         300.00 USD
          Assets:DIT:Savings
        
        2000-04-01 * "Checking" "Cannot merge because of price conversion"
          Assets:Savings         -440.00 USD
          Assets:DIT:Checking     400.00 CAD @ 1.1000 USD
        
        2000-04-01 * "Savings" "Cannot merge because of price conversion"
          Assets:Checking         400.00 CAD
          Assets:DIT:Savings
        
        2000-05-01 * "This narration should appear after the next"
          Assets:Checking         123.00 USD
          Assets:DIT:Savings
        
        2000-05-01 * "This narration should appear before the previous"
          Assets:Savings         -123.00 USD
          Assets:DIT:Checking
        """
        self.assertFalse(errors)
        self.assertEqualEntries("""
        2000-01-01 open Assets:Checking
        2000-01-01 open Assets:Savings
        2000-01-01 open Liabilities:Visa
        2000-02-01 open Assets:DIT:Checking
        2000-02-01 open Assets:DIT:Savings
        
        2000-02-01 * "This transaction should be merged with the next / This transaction should be merged with the previous" #DEPOSITED
          Assets:Savings        -500.00 USD
          Assets:Checking        500.00 USD
        
        2000-02-07 open Liabilities:DIT:Visa
        
        2000-02-07 * "Visa" "This transaction should be linked to the next" #DEPOSITED ^deposited-1
          Assets:Checking       -100.00 USD
          Liabilities:DIT:Visa   100.00 USD
        
        2000-02-09 * "Visa" "This transaction should be linked to the next / This transaction should be linked to the previous" #DEPOSITED ^deposited-1
          Liabilities:DIT:Visa  -100.00 USD
          Assets:DIT:Checking    100.00 USD
        
        2000-02-09 * "This transaction should be linked to the previous" #DEPOSITED ^deposited-1
          Liabilities:Visa      100.00 USD
          Assets:DIT:Checking  -100.00 USD
        
        2000-03-01 ! "The Bank" "Cannot merge because of different flags" #DEPOSITED ^deposited-2
          Assets:Savings       -300.00 USD
          Assets:DIT:Checking   300.00 USD
        
        2000-03-01 * "The Bank" "Cannot merge because of different flags" #DEPOSITED ^deposited-2
          Assets:DIT:Checking  -300.00 USD
          Assets:DIT:Savings    300.00 USD
        
        2000-03-01 * "The Bank" "Cannot merge because of different flags" #DEPOSITED ^deposited-2
          Assets:Checking      300.00 USD
          Assets:DIT:Savings  -300.00 USD
        
        2000-03-08 ! "This transaction should be tagged pending" #IN-TRANSIT
          Assets:Checking       -150.00 USD
          Liabilities:DIT:Visa   150.00 USD
        
        2000-04-01 * "Checking" "Cannot merge because of price conversion" #DEPOSITED ^deposited-3
          Assets:Savings       -440.00 USD             
          Assets:DIT:Checking   400.00 CAD @ 1.1000 USD
        
        2000-04-01 * "Checking / Savings" "Cannot merge because of price conversion" #DEPOSITED ^deposited-3
          Assets:DIT:Checking  -400.00 CAD
          Assets:DIT:Savings    400.00 CAD
        
        2000-04-01 * "Savings" "Cannot merge because of price conversion" #DEPOSITED ^deposited-3
          Assets:Checking      400.00 CAD
          Assets:DIT:Savings  -400.00 CAD
        
        2000-05-01 * "This narration should appear before the previous / This narration should appear after the next" #DEPOSITED
          Assets:Savings      -123.00 USD
          Assets:Checking      123.00 USD
        """, entries)

    @loader.load_doc(expect_errors=True)
    def test_options_parser(self, entries, errors, _):
        """
        plugin "beansoup.plugins.deposit_in_transit" "
        --not_an_option --same_day_merge --flag_pending --link_prefix=deposited"
        
        2000-01-01 open Assets:Checking
        2000-01-01 open Assets:Savings
        
        2000-02-07 * "Just an entry"
          Assets:Savings        -100.00 USD
          Assets:Checking
        """
        # There will be warnings about the DIT unknown accounts
        self.assertEqual(len(errors), 1)
        self.assertEqual(type(errors[0]), config.ParseError)
        self.assertEqualEntries("""
        2000-01-01 open Assets:Checking
        2000-01-01 open Assets:Savings
        
        2000-02-07 * "Just an entry"
          Assets:Savings        -100.00 USD
          Assets:Checking        100.00 USD
        """, entries)

    @loader.load_doc(expect_errors=True)
    def test_disable_option(self, entries, errors, _):
        """
        plugin "beansoup.plugins.deposit_in_transit" "
        --skip_re=setup.py --auto_open --same_day_merge --flag_pending"
        
        2000-01-01 open Assets:Checking
        2000-01-01 open Assets:Savings
        2000-01-01 open Liabilities:Visa
        
        2000-02-01 * "This transaction should be merged with the next"
          Assets:Savings         -500.00 USD
          Assets:DIT:Checking
        
        2000-02-01 * "This transaction should be merged with the previous"
          Assets:Checking         500.00 USD
          Assets:DIT:Savings
        """
        # There will be warnings about the DIT unknown accounts
        self.assertEqual(len(errors), 2)
        self.assertEqualEntries("""
        2000-01-01 open Assets:Checking
        2000-01-01 open Assets:Savings
        2000-01-01 open Liabilities:Visa
        
        2000-02-01 * "This transaction should be merged with the next"
          Assets:Savings         -500.00 USD
          Assets:DIT:Checking     500.00 USD
        
        2000-02-01 * "This transaction should be merged with the previous"
          Assets:Checking         500.00 USD
          Assets:DIT:Savings     -500.00 USD
        """, entries)

    @loader.load_doc(expect_errors=True)
    def test_multiple_dits_entry(self, entries, errors, _):
        """
        plugin "beansoup.plugins.deposit_in_transit" "
        --auto_open --same_day_merge --flag_pending --link_prefix=deposited"
        
        2000-01-01 open Assets:Checking
        2000-01-01 open Assets:Savings
        2000-01-01 open Liabilities:Visa
        
        2000-02-07 * "Visa" "This transaction should be linked to the next"
          Assets:Checking        -200.00 USD
          Liabilities:DIT:Visa    100.00 USD
          Assets:DIT:Savings
        
        2000-02-09 * "This transaction should be linked to the previous"
          Liabilities:Visa        100.00 USD
          Assets:DIT:Checking
        """
        # There will be warnings about the DIT unknown accounts
        self.assertEqual(len(errors), 1)
        self.assertEqual(type(errors[0]), deposit_in_transit.DITError)
        self.assertEqualEntries("""
        2000-02-07 * "Visa" "This transaction should be linked to the next"
          Assets:Checking       -200.00 USD
          Liabilities:DIT:Visa   100.00 USD
          Assets:DIT:Savings     100.00 USD
        """, [errors[0].entry])
        self.assertEqualEntries("""
        2000-01-01 open Assets:Checking
        2000-01-01 open Assets:Savings
        2000-01-01 open Liabilities:Visa
        2000-02-07 open Assets:DIT:Savings
        2000-02-07 open Liabilities:DIT:Visa
        
        2000-02-07 * "Visa" "This transaction should be linked to the next" #DEPOSITED ^deposited-1
          Assets:Checking       -200.00 USD
          Liabilities:DIT:Visa   100.00 USD
          Assets:DIT:Savings     100.00 USD
        
        2000-02-09 open Assets:DIT:Checking
        
        2000-02-09 * "Visa" "This transaction should be linked to the next / This transaction should be linked to the previous" #DEPOSITED ^deposited-1
          Liabilities:DIT:Visa  -100.00 USD
          Assets:DIT:Checking    100.00 USD
        
        2000-02-09 * "This transaction should be linked to the previous" #DEPOSITED ^deposited-1
          Liabilities:Visa      100.00 USD
          Assets:DIT:Checking  -100.00 USD
        """, entries)
