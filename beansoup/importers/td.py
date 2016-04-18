"""Importers for TD Canada Trust."""

import csv as csvlib
import datetime

from beancount.core.number import D

from beansoup.importers import csv


csvlib.register_dialect('tdcanadatrust', delimiter=',', quoting=csvlib.QUOTE_MINIMAL)


class Importer(csv.Importer):
    """An importer for TD Canada Trust CSV statements."""
    def parse(self, file):
        """Parse a TD Canada Trust CSV file.

        Args:
          file: A beansoup.ingest.cache.FileMemo instance; the CSV file to be parsed.
        Returns:
          A list of Row objects.
        """
        return csv.parse(file, 'tdcanadatrust', self.parse_row)

    def parse_row(self, row, lineno):
        """Parse a row of a TD Canada Trust CSV file.
    
        Args:
          row: A list of field values for the row.
          lineno: The line number where the row appears in the CSV file
        Returns:
          A beansoup.importers.csv.Row object.
        """
        if len(row) != 5:
            raise csvlib.Error('Invalid row; expecting 5 values: {}'.format(row))
        date = datetime.datetime.strptime(row[0], '%m/%d/%Y').date()
        description = row[1]
        amount = -D(row[2]) if row[2] else D(row[3])
        balance = self.account_sign * D(row[4])
        return csv.Row(lineno, date, description, amount, balance)
