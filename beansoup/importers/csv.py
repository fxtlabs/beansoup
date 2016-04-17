"""CSV Importers."""

import csv
import datetime
import itertools
import logging
from os import path
import re

from beancount.core import account_types as atypes
from beancount.core import amount
from beancount.core import data
from beancount.ingest import importer
from beancount.parser import options

from beansoup.utils import periods


class Importer(importer.ImporterProtocol):
    """An importer base class for CSV bank and credit card statements.

    Unfortunately, CSV files often do not contain any information to easily
    identify the account; for this reason, this importer relies on the name
    of the file to associate it to a particular account.

    Derived classes need to implement the 'parse' method.

    See beansoup.importers.td.Importer for a full example of how to derive a
    concrete importer from this class.
    """
    def __init__(self, account, currency='CAD', basename=None,
                 first_day=None, filename_regexp=None, account_types=None):
        """Create a new importer for the given account.

        Args:
          account: An account string, the account to associate to the files.
          account_types: An AccountTypes object or None to use the default ones.
          basename: An optional string, the name of the new files.
          currency: A string, the currency for all extracted transactions.
          filename_regexp: A regular expression string used to match the
            basename (no path) of the target file.
          first_day: An int in [1,28]; the first day of the statement/billing
            period or None. If None, the file date will be the date of the
            last extracted entry; otherwise, it will be the date of the end
            of the monthly period containing the last extracted entry.
            Also, if a balance directive can be generated, if None, the balance
            directive will be set to the day following the date of the last
            extracted entry; otherwise, it will be set to the day following the
            end of the statement period.
        """
        self.filename_re = re.compile(filename_regexp or self.filename_regexp)
        self.account = account
        self.currency = currency.upper()
        self.basename = basename
        self.first_day = first_day
        self.account_sign = atypes.get_account_sign(account, account_types)

    def name(self):
        """Include the account in the name."""
        return '{}: "{}"'.format(super().name(), self.file_account(None))

    def identify(self, file):
        """Identify whether the file can be processed by this importer."""
        # Match for a compatible MIME type.
        if file.mimetype() != 'text/csv':
            return False

        # Match the file name.
        return self.filename_re.match(path.basename(file.name))

    def file_account(self, _):
        """Return the account associated with the file"""
        return self.account

    def file_name(self, file):
        """Return the optional renamed account file name."""
        if self.basename:
            return self.basename + path.splitext(file.name)[1]

    def file_date(self, file):
        """Return the filing date for the file."""
        rows = self.parse(file)
        date = max(row.date for row in rows)
        if self.first_day is not None:
            date = periods.lowest_end(date, first_day=self.first_day)
        return date

    def extract(self, file):
        """Return extracted entries and errors."""
        rows = self.parse(file)
        rows, error_lineno = sort_rows(rows, self.account_sign)
        new_entries = []
        if len(rows) == 0:
            return new_entries

        for index, row in enumerate(rows):
            posting = data.Posting(
                self.account,
                amount.Amount(row.amount, self.currency),
                None, None, None, None)
            # Use the final positional index rather than the lineno of the row so we can
            # later sort the entries to merge them with the balance entries
            meta = data.new_metadata(file.name, index)
            payee = None
            narration = row.description
            entry = data.Transaction(
                meta,
                row.date,
                self.FLAG,
                payee,
                narration,
                None,
                None,
                [posting])
            new_entries.append(entry)

        # Extract balance, but only if we can trust it
        if error_lineno is not None:
            logging.warning('{}:{}: cannot reorder rows to agree with balance values'.format(
                file.name, error_lineno))
        elif self.first_day is None:
            # Create one single balance entry on the day following the last transaction
            last_row = rows[-1]
            date = last_row.date + datetime.timedelta(days=1)
            balance_entry = self.create_balance_entry(
                file.name, last_row.lineno, date, last_row.balance)
            new_entries.append(balance_entry)
        else:
            # Create monthly balance entries starting from the most recent one
            balance_date = periods.next(periods.greatest_start(rows[-1].date,
                                                               first_day=self.first_day))
            for row in reversed(rows):
                if row.date < balance_date:
                    new_entries.append(self.create_balance_entry(
                        file.name, balance_date, row.balance))
                    balance_date = periods.prev(balance_date)
            
        return data.sorted(new_entries)

    def create_balance_entry(self, filename, date, balance_number):
        balance = self.account_sign * balance_number
        meta = data.new_metadata(filename, 0)
        balance_entry = data.Balance(meta, date, self.account,
                                     amount.Amount(balance, self.currency),
                                     None, None)
        return balance_entry

    def parse(self, file):
        """Parse the CSV file.

        Derived classes must implement this method to parse their CSV files.
        A typical implementation will be:
          return file.convert(parse)
        where 'parse' will be a function doing the actual parsing. This allows the result
        of the parser to be reused by multiple importers (those sharing the 'parse'
        function); in order for the caching to work correctly, the 'parse' function must
        not depend on any information other than the name of the file to be parsed.

        Consider using the helper function 'beansoup.importers.csv.parse' to implement
        your custom CSV parser.

        Args:
          file: A cache.FileMemo object.
        Returns:
          A list of object; on object per row; each object is expected to have the
          following attributes:
            lineno: An int, the line of the CSV file where this row is found.
            date: A datetime.date object; the date of the transaction.
            description: A string; a description of the transaction.
            amount: A Decimal object; the value of the transaction; the sign of its value
              should be the same as normally used by beancount entries.
            balance: A Decimal object; the balance of the account immediately following
              the transaction; the natural sign of its value is expected to be positive;
              the importer will adjust it as necessary for liabilities accounts.
          The order of the parsed rows is irrelevant; they will be sorted in ascending
          chronological order in a way that agrees with the balance values associated to
          each row. It that is not possible, the balance values will be ignored and the
          importer will be unable to extract balance directive, but will otherwise work
          as expected.
        """
        raise NotImplementedError('Derived classes must implement this method.')


def parse(filename, dialect, parse_row):
    """Parse a CSV file.

    Args:
      filename: The name of the CSV file to be parsed.
      dialect: The name of a registered CSV dialect to use for parsing.
      parse_row: A function taking a row (a list of values) and its line number in
        the input file and returning an object with the following attributes:
          lineno: An int, the line of the CSV file where this row is found.
          date: A datetime.date object; the date of the transaction.
          description: A string; a description of the transaction.
          amount: A Decimal object; the value of the transaction; the sign of its value
            should be the same as normally used by beancount entries.
          balance: A Decimal object; the balance of the account immediately following
            the transaction; the natural sign of its value is expected to be positive;
            the importer will adjust it as necessary for liabilities accounts.
    Returns:
      A list of objects with attributes as described for the return value of the
      'parse_row' function above.
    """
    with open(filename, newline='') as file:
        reader = csv.reader(file, dialect)
        try:
            rows = [parse_row(row, reader.line_num) for row in reader]
        except (csv.Error, ValueError) as exc:
            logging.error('{}:{}: {}'.format(filename, reader.line_num, exc))
            rows = []
    return rows


def sort_rows(rows, account_sign):
    """Sort the rows of a CSV file.

    This function can sort the rows of a CSV file in ascending chronological order
    such that the balance values of each row match the sequence of transactions.

    Args:
      rows: A list of objects with a lineno, date, amount, and balance attributes.
      account_sign: The sign of the account the CSV rows belong to.
    Returns
      A pair with a sorted list of rows and an error. The error is None if the function
      could find an ordering agreeing with the balance values of its rows; otherwise,
      it is the line number in the CSV file corresponding to the first row not agreeing
      with its balance value.
    """
    if len(rows) <= 1:
        return rows, None

    # If there is more than one row sharing the earliest date of the statement, we do not
    # know for sure which one came first, so we have a number of opening balances and we
    # have to find out which one is the right one.
    first_date = rows[0].date
    opening_balances = [account_sign * row.balance - row.amount for row in itertools.takewhile(
        lambda r: r.date == first_date, rows)]

    error_lineno = 0
    for opening_balance in opening_balances:
        # Given one choice of opening balance, we try to find an ordering of the rows
        # that agrees with the balance amount they show
        stack = list(reversed(rows))
        prev_balance = opening_balance
        unbalanced_rows = []
        balanced_rows = []
        while stack:
            row = stack.pop()
            # Check if the current row balances with the previous one
            balance = account_sign * row.balance
            if prev_balance + row.amount == balance:
                # The current row is in the correct chronological order
                balanced_rows.append(row)
                prev_balance = balance
                if unbalanced_rows:
                    # Put unbalanced rows back on the stack so they get another chance
                    stack.extend(unbalanced_rows)
                    unbalanced_rows.clear()
            else:
                # The current row is out of chronological order
                if unbalanced_rows and unbalanced_rows[0].date != row.date:
                    # No ordering can be found that agrees with the balance values of the rows
                    break
                # Skip the current row for the time being
                unbalanced_rows.append(row)
        if len(balanced_rows) == len(rows):
            return balanced_rows, None
        error_lineno = unbalanced_rows[0].lineno

    # The rows could not be ordered in any way that would agree with the balance values
    return rows, error_lineno
