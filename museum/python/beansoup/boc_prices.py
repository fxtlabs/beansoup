# -*- coding: utf-8 -*-
"""
TODO:
- set up emacs for beancount-mode
  See Editor Support in https://docs.google.com/document/d/1FqyrTPwiHVLyncWTf3v5TcooCu9z5JRX8Nm41lVZi0U/edit#
- look at beancount/scripts/bake.py for inspiration
- look at the beancount/prices/price.py script; I could draw from it to write
  a script to find all the dates when commodities held at cost in USD were
  traded so that I could have a list of dates to fetch USD/CAD exchange rates
- implement beancount.prices.source.Source source for BOC
- implement beancount.prices.source.Source interface for a beancount file of
  price directives!
- better module name (boc_prices is not so inspiring)
- better module docstring
  See http://sphinxcontrib-napoleon.readthedocs.org/en/latest/example_google.html
- add command line arg to sort in descending chronological order
- add command line arg to save to a file
- add support to read from stdin
- look at using FileType for command line arg
- write setup.py file for the package
- for bank holidays, use the exchange rate from the previous day(s)
- structure package to follow beancount conventions
- improve error handling
- improve error reporting
- support multiple currencies
- look into other file formats (BOC SDMX in particular; sdmx.org)

===============
In order to get XXX/CAD exchange rates from the Bank of Canada:
- go to http://www.bankofcanada.ca/rates/exchange/10-year-lookup/
- select start and end dates and exactly one currency
- submit the form
- download the csv file from the results page

This above is a bit of a pain. Using
http://www.quandl.com/api/v1/datasets/BOE/XUDLCDD
would be a lot more automatic (JSON response), but the rates from Bank of England
do not exactly match those from Bank of Canada
See http://www.quandl.com/help/api-for-currency-data
https://www.quandl.com/data/BOE/XUDLCDD-Spot-exchange-rate-Canadian-Dollar-into-US
"""

import argparse
from datetime import date
import logging
import re

from beancount.core.data import Amount, Price
from beancount.core.number import D
from beancount.parser.printer import print_entries

logger = logging.getLogger(__name__)

currency_re = re.compile(r"^Date,(?P<currency>\w+)")
price_re = re.compile(r"^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2}),\s*(?P<rate>\d+(\.\d*)?)")


def parse_price(currency, line):
    m = price_re.match(line)
    if m:
        d = m.groupdict()
        return Price({},
                     date(int(d['year']), int(d['month']), int(d['day'])),
                     currency,
                     Amount(D(d['rate']), 'CAD'))


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
                price = parse_price(currency, line)
                if price:
                    prices.append(price)
                else:
                    logger.warning('Parse error (%d): %s\n', lineno, line)
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
    prices = sorted(prices, key=lambda p: p.date)
    print_entries(prices)
    return 0
