"""Importers for TD Canada Trust."""

import collections
import csv
import datetime

from beancount.core.number import D

from beansoup.importers import csv as csvimp


class Importer(csvimp.Importer):
    """An importer for TD Canada Trust CSV statements."""
    def parse(self, file):
        return file.convert(parse)


csv.register_dialect('tdcanadatrust', delimiter=',', quoting=csv.QUOTE_MINIMAL)

Row = collections.namedtuple('Row', 'lineno date description amount balance')


def parse(filename):
    """Parse a TD Canada Trust CSV file.

    Args:
      filename: The name of the CSV file to be parsed.
    Returns:
      A list of Row objects.
    """
    return csvimp.parse(filename, 'tdcanadatrust', parse_row)


def parse_row(row, lineno):
    """Parse a row of a TD Canada Trust CSV file.

    Args:
      row: A list of field values for the row.
      lineno: The line number where the row appears in the CSV file
    Returns:
      A Row object with lineno (an int, the line of the CSV file where this row is found),
      date (a datetime.date object), description (a string), amount (a Decimal object),
      and balance (another Decimal object).
    """
    date = datetime.datetime.strptime(row[0], '%m/%d/%Y').date()
    description = row[1]
    amount = -D(row[2]) if row[2] else D(row[3])
    balance = D(row[4])
    return Row(lineno, date, description, amount, balance)
