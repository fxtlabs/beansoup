# -*- coding: utf-8 -*-

# In order to get XXX/CAD exchange rates from the Bank of Canada:
# - go to http://www.bankofcanada.ca/rates/exchange/10-year-lookup/
# - select start and end dates and exactly one currency
# - submit the form
# - download the csv file from the results page
#
# This above is a bit of a pain. Using
# http://www.quandl.com/api/v1/datasets/BOE/XUDLCDD
# would be a lot more automatic (JSON response), but the rates from Bank of England
# do not exactly match those from Bank of Canada
# See http://www.quandl.com/help/api-for-currency-data

import argparse
from datetime import date
import logging
import re

from beancount.core.data import Amount, Price, FileLocation
from beancount.parser.printer import print_entries

currency_re = re.compile(r"^Date,(?P<currency>\w+)")
price_re = re.compile(r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2}),\s*(?P<rate>\d+(\.\d*)?)")


def parse_price(fileloc, currency, line):
    m = price_re.match(line)
    if m:
        d = m.groupdict()
        return Price(fileloc,
                     date(int(d['year']), int(d['month']), int(d['day'])),
                     currency,
                     Amount(d['rate'], 'CAD'))


def parse_currency(line):
    m = currency_re.match(line)
    if m:
        d = m.groupdict()
        return d['currency']


def parse_prices(filename):
    currency = None
    with open(filename, 'r') as f:
        prices = []
        # The file indicates which currency the rates are for in its
        # first few lines; after that, the list of rates follows, one
        # per line
        for lineno, line in enumerate(f.readlines()):
            if currency:
                price = parse_price(FileLocation(filename, lineno), currency, line)
                if price:
                    prices.append(price)
            else:
                currency = parse_currency(line)
    assert currency is not None, "Cannot determine currency of exchange rates"
    
    return prices


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s: %(message)s')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('filename',
                        help='Bank of Canada exchange rates 10-year lookup CSV file (http://www.bankofcanada.ca/rates/exchange/10-year-lookup/)')
    opts = parser.parse_args()

    prices = parse_prices(opts.filename)
    print_entries(prices)
