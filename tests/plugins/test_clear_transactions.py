"""Unit tests for deposit_in_transit plugin."""

from beancount import loader
from beancount.parser import cmptest

from beansoup.plugins import config
from beansoup.plugins import clear_transactions


class TestClearTransactions(cmptest.TestCase):

    @loader.load_doc()
    def test_plugin(self, entries, errors, _):
        """
        plugin "beansoup.plugins.clear_transactions" "
        --flag_pending
        Assets:Clearing:Checking,Assets:Checking
        Liabilities:Clearing:Visa,Liabilities:Visa"
        
        2000-01-01 open Assets:Savings
        2000-01-01 open Assets:Checking
        2000-01-01 open Assets:Clearing:Checking
        2000-01-01 open Liabilities:Visa
        2000-01-01 open Liabilities:Clearing:Visa
        
        2000-02-01 * "This transaction should be linked to the next"
          Assets:Savings         -500.00 USD
          Assets:Clearing:Checking
        
        2000-02-01 * "This transaction should be linked to the previous"
          Assets:Checking         500.00 USD
          Assets:Clearing:Checking
        
        2000-03-01 * "This transaction should be ignored" #PRE_CLEARED
          Assets:Savings         -400.00 USD
          Assets:Clearing:Checking
        
        2000-03-01 * "This transaction should be ignored" #PRE_CLEARED
          Assets:Checking         400.00 USD
          Assets:Clearing:Checking
        
        2000-02-07 * "Visa" "This transaction should be linked to the next"
          Assets:Checking        -100.00 USD
          Liabilities:Clearing:Visa
        
        2000-02-10 * "This transaction should be linked to the previous"
          Liabilities:Visa        100.00 USD
          Liabilities:Clearing:Visa
        
        2000-02-08 * "Visa" "This transaction should be linked to the next"
          Assets:Checking        -100.00 USD
          Liabilities:Clearing:Visa
        
        2000-02-11 * "This transaction should be linked to the previous"
          Liabilities:Visa        100.00 USD
          Liabilities:Clearing:Visa
        
        2000-02-09 * "Visa" "This transaction should be linked to the next"
          Assets:Checking        -120.00 USD
          Liabilities:Clearing:Visa
        
        2000-02-09 * "This transaction should be linked to the previous"
          Liabilities:Visa        120.00 USD
          Liabilities:Clearing:Visa
        
        2000-03-07 * "Visa" "This transaction should not be linked to the next"
          Assets:Checking        -100.00 USD
          Liabilities:Clearing:Visa
        
        2000-03-19 * "This transaction should be not linked to the previous"
          Liabilities:Visa        100.00 USD
          Liabilities:Clearing:Visa
        
        2000-04-08 * "This transaction should be tagged pending"
          Assets:Checking        -150.00 USD
          Liabilities:Clearing:Visa
        """
        self.assertFalse(errors)
        self.assertEqualEntries("""
        2000-01-01 open Assets:Savings
        2000-01-01 open Assets:Checking
        2000-01-01 open Assets:Clearing:Checking
        2000-01-01 open Liabilities:Visa
        2000-01-01 open Liabilities:Clearing:Visa
        
        2000-02-01 * "This transaction should be linked to the next" #CLEARED ^cleared-1
          Assets:Savings            -500.00 USD
          Assets:Clearing:Checking   500.00 USD
        
        2000-02-01 * "This transaction should be linked to the previous" #CLEARED ^cleared-1
          Assets:Checking            500.00 USD
          Assets:Clearing:Checking  -500.00 USD
        
        2000-02-07 * "Visa" "This transaction should be linked to the next" #CLEARED ^cleared-2
          Assets:Checking            -100.00 USD
          Liabilities:Clearing:Visa   100.00 USD
        
        2000-02-08 * "Visa" "This transaction should be linked to the next" #CLEARED ^cleared-3
          Assets:Checking            -100.00 USD
          Liabilities:Clearing:Visa   100.00 USD
        
        2000-02-09 * "Visa" "This transaction should be linked to the next" #CLEARED ^cleared-4
          Assets:Checking            -120.00 USD
          Liabilities:Clearing:Visa   120.00 USD
        
        2000-02-09 * "This transaction should be linked to the previous" #CLEARED ^cleared-4
          Liabilities:Visa            120.00 USD
          Liabilities:Clearing:Visa  -120.00 USD
        
        2000-02-10 * "This transaction should be linked to the previous" #CLEARED ^cleared-2
          Liabilities:Visa            100.00 USD
          Liabilities:Clearing:Visa  -100.00 USD
        
        2000-02-11 * "This transaction should be linked to the previous" #CLEARED ^cleared-3
          Liabilities:Visa            100.00 USD
          Liabilities:Clearing:Visa  -100.00 USD
        
        2000-03-01 * "This transaction should be ignored" #PRE_CLEARED
          Assets:Savings            -400.00 USD
          Assets:Clearing:Checking   400.00 USD
        
        2000-03-01 * "This transaction should be ignored" #PRE_CLEARED
          Assets:Checking            400.00 USD
          Assets:Clearing:Checking  -400.00 USD
        
        2000-03-07 ! "Visa" "This transaction should not be linked to the next" #PENDING
          Assets:Checking            -100.00 USD
          Liabilities:Clearing:Visa   100.00 USD
        
        2000-03-19 ! "This transaction should be not linked to the previous" #PENDING
          Liabilities:Visa            100.00 USD
          Liabilities:Clearing:Visa  -100.00 USD
        
        2000-04-08 ! "This transaction should be tagged pending" #PENDING
          Assets:Checking            -150.00 USD
          Liabilities:Clearing:Visa   150.00 USD
        """, entries)

    @loader.load_doc()
    def test_skip_weekends_option(self, entries, errors, _):
        """
        plugin "beansoup.plugins.clear_transactions" "
        --skip_weekends --flag_pending
        Assets:Clearing:Checking,Assets:Checking
        Liabilities:Clearing:Visa,Liabilities:Visa"
        
        2000-01-01 open Assets:Savings
        2000-01-01 open Assets:Checking
        2000-01-01 open Assets:Clearing:Checking
        2000-01-01 open Liabilities:Visa
        2000-01-01 open Liabilities:Clearing:Visa
        
        2000-02-01 * "This transaction should be linked to the next"
          Assets:Savings         -500.00 USD
          Assets:Clearing:Checking
        
        2000-02-09 * "This transaction should be linked to the previous"
          Assets:Checking         500.00 USD
          Assets:Clearing:Checking
        
        2000-03-07 * "Visa" "This transaction should not be linked to the next"
          Assets:Checking        -100.00 USD
          Liabilities:Clearing:Visa
        
        2000-03-17 * "This transaction should not be linked to the previous"
          Liabilities:Visa        100.00 USD
          Liabilities:Clearing:Visa
        """
        self.assertFalse(errors)
        self.assertEqualEntries("""
        2000-01-01 open Assets:Savings
        2000-01-01 open Assets:Checking
        2000-01-01 open Assets:Clearing:Checking
        2000-01-01 open Liabilities:Visa
        2000-01-01 open Liabilities:Clearing:Visa
        
        2000-02-01 * "This transaction should be linked to the next" #CLEARED ^cleared-1
          Assets:Savings            -500.00 USD
          Assets:Clearing:Checking   500.00 USD
        
        2000-02-09 * "This transaction should be linked to the previous" #CLEARED ^cleared-1
          Assets:Checking            500.00 USD
          Assets:Clearing:Checking  -500.00 USD
        
        2000-03-07 ! "Visa" "This transaction should not be linked to the next" #PENDING
          Assets:Checking            -100.00 USD
          Liabilities:Clearing:Visa   100.00 USD
        
        2000-03-17 ! "This transaction should not be linked to the previous" #PENDING
          Liabilities:Visa            100.00 USD
          Liabilities:Clearing:Visa  -100.00 USD
        """, entries)

    @loader.load_doc(expect_errors=True)
    def test_options_parser_1(self, entries, errors, _):
        """
        plugin "beansoup.plugins.clear_transactions" "
        --flag_pending
        Assets:Clearing:Checking;Assets:Checking
        Liabilities:Clearing:Visa,Liabilities:Visa"
        
        2000-01-01 open Assets:Savings
        2000-01-01 open Assets:Checking
        2000-01-01 open Assets:Clearing:Checking
        2000-01-01 open Liabilities:Visa
        2000-01-01 open Liabilities:Clearing:Visa
        """
        self.assertEqual(len(errors), 1)
        self.assertEqual(type(errors[0]), config.ParseError)
        self.assertEqualEntries("""
        2000-01-01 open Assets:Savings
        2000-01-01 open Assets:Checking
        2000-01-01 open Assets:Clearing:Checking
        2000-01-01 open Liabilities:Visa
        2000-01-01 open Liabilities:Clearing:Visa
        """, entries)

    @loader.load_doc(expect_errors=True)
    def test_options_parser_2(self, entries, errors, _):
        """
        plugin "beansoup.plugins.clear_transactions" "
        --flag_pending
        Assets:Clearing:Checking,Assets:Checking
        Assets:Clearing:Visa,Liabilities:Visa"
        
        2000-01-01 open Assets:Savings
        2000-01-01 open Assets:Checking
        2000-01-01 open Assets:Clearing:Checking
        2000-01-01 open Liabilities:Visa
        2000-01-01 open Liabilities:Clearing:Visa
        """
        self.assertEqual(len(errors), 1)
        self.assertEqual(type(errors[0]), config.ParseError)
        self.assertEqualEntries("""
        2000-01-01 open Assets:Savings
        2000-01-01 open Assets:Checking
        2000-01-01 open Assets:Clearing:Checking
        2000-01-01 open Liabilities:Visa
        2000-01-01 open Liabilities:Clearing:Visa
        """, entries)
