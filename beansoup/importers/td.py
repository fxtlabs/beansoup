"""Importers for TD Canada Trust."""

import csv
import collections
import datetime
import itertools
import logging
from os import path
import re

from beancount.core import account_types as atypes
from beancount.core import amount
from beancount.core import data
from beancount.core.number import D
from beancount.ingest import importer
from beancount.parser import options

from beansoup.utils import period


class Importer(importer.ImporterProtocol):
    """An importer for TD Canada Trust CSV statements.

    Unfortunately, these CSV files do not contain any information to easily
    identify the account; for this reason, this importer relies on the name
    of the file to associate it to a particular account.
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
        rows, _ = self.parse(file)
        date = max(row.date for row in rows)
        if self.first_day is not None:
            _, date = period.enclose_date(date, first_day=self.first_day)
        return date

    def extract(self, file):
        """Return extracted entries and errors."""
        rows = self.parse(file)
        rows, error_lineno = sort_rows(rows, self.account_sign)
        new_entries = []
        for row in rows:
            posting = data.Posting(
                self.account,
                amount.Amount(row.amount, self.currency),
                None, None, None, None)
            meta = data.new_metadata(file.name, row.lineno)
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
        if rows and error_lineno is None:
            last_row = rows[-1]
            balance = self.account_sign * last_row.balance
            # The Balance assertion occurs at the beginning of the date,
            # so move it to the following day.
            date = last_row.date + datetime.timedelta(days=1)
            meta = data.new_metadata(file.name, last_row.lineno)
            balance_entry = data.Balance(meta, date, self.account,
                                         amount.Amount(balance, self.currency),
                                         None, None)
            new_entries.append(balance_entry)
        elif rows:
            logging.warning('{}:{}: cannot reorder rows to agree with balance values'.format(
                file.name, error_lineno))

        # Do not sort the entries before returning them; their lineno might lead to reverting
        # all the work sort_rows() did to figure out the correct order!

        return new_entries

    def parse(self, file):
        return file.convert(parse)


csv.register_dialect('tdcanadatrust', delimiter=',', quoting=csv.QUOTE_MINIMAL)

Row = collections.namedtuple('Row',
                                'lineno date description amount balance')

def parse(filename):
    """Parse a TD Canada Trust CSV file.

    Args:
      filename: The name of the CSV file to be parsed.
    Results:
      A pair with the list of Row objects in ascending chronological order
      and the account sign. The latter may be zero if the correct sign could
      not be determined; this would also indicate that the balance values
      cannot be trusted.
    """
    with open(filename, newline='') as file:
        reader = csv.reader(file, 'tdcanadatrust')
        try:
            rows = [parse_row(row, reader.line_num) for row in reader]
        except (csv.Error, ValueError) as exc:
            logging.error('{}:{}: {}'.format(filename, reader.line_num, exc))
            rows = []
    return rows


def parse_row(row, lineno):
    date = datetime.datetime.strptime(row[0], '%m/%d/%Y').date()
    description = row[1]
    amount = -D(row[2]) if row[2] else D(row[3])
    balance = D(row[4])
    return Row(lineno, date, description, amount, balance)


def sort_rows_guess_sign(rows, filename):
    if len(rows) <= 1:
        return rows, 0

    # Sort the rows by their date; this is only a partial chronological order.
    # We do not know yet whether rows that share the same date are in an order that is
    # consistent with the balance amount they show
    rows.sort(key=lambda x: x.date)

    balanced_rows, error_lineno = sort_rows(rows, +1)
    if error_lineno is None:
        print("IT IS ASSET")
        return balanced_rows, +1
    
    balanced_rows, error_lineno = sort_rows(rows, -1)
    if error_lineno is None:
        print("IT IS LIABILITY")
        return balanced_rows, -1

    logging.warning('{}:{}: cannot reorder rows to agree with balance values'.format(filename, error_lineno))

    return rows, 0


def sort_rows(rows, account_sign):
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


def sort_rows_orig(rows):
    if len(rows) <= 1:
        return rows

    stack = sorted(rows, key=lambda x: x.date, reverse=True)
    # Assume the first row is really the first transaction

    prev_row = stack.pop()
    unmatched = []
    outrows = [prev_row]
    while stack:
        row = stack.pop()
        # Check if the current row balances with the previous one
        if prev_row.balance + row.amount == row.balance:
            # The current row is in the correct chronological order
            outrows.append(row)
            prev_row = row
            if unmatched:
                # Put unmatched rows back on the stack so they get another chance
                stack.extend(unmatched)
                unmatched.clear()
        else:
            # The current row is out of chronological order
            if unmatched and unmatched[0].date != row.date:
                # No ordering can be found that agrees with the balance amount of the rows
                break
            # Skip the current row for the time being
            unmatched.append(row)
    if unmatched:
        # The rows could not be ordered in any way that would agree with the balance values
        logging.warning('NO SORT: {} rows unmatched'.format(len(unmatched)))
    return outrows


def adjust(rows):
    # FIXME: factor out the following code so other parsers can use it.
    # It should probably be located in the importers package.

    # We assume the rows are in chronological order, but we do not know
    # whether ascending or descending.
    # Try to put them in ascending order and determine the account sign.
    if len(rows) <= 1:
        account_sign = 0
    else:
        account_sign = +1
        first_date = rows[0].date
        last_date = rows[-1].date
        if first_date != last_date:
            # Sort rows in ascending chronological order
            if last_date < first_date:
                rows.reverse()
            # Determine whether the sign of the balance entries should be
            # reversed; if so, it must be a liabilities account.
            if not check_balance(rows, +1):
                account_sign = -1 if check_balance(rows, -1) else 0
        else:
            # This is the hard case; all rows share the same date
            if not check_balance(rows, +1):
                # Either the rows are in reverse order, or this is a
                # liabilities account or both; let's try reversing the order.
                rows.reverse()
                if not check_balance(rows, +1):
                    # This must be a liabilities account; let's reverse the
                    # sign of the balance
                    account_sign = -1
                    if not check_balance(rows, -1):
                        # The rows must be in reverse order
                        rows.reverse()
                        if not check_balance(rows, -1):
                            # We cannot determine the account sign and
                            # cannot trust the balance values
                            account_sign = 0

    if account_sign == 0:
        logging.error('{}:0: Cannot determine account sign'.format(filename))

    return rows, account_sign


def check_balance(rows, account_sign):
    rows_iter = iter(rows)
    prev_balance = account_sign * next(rows_iter).balance
    import pdb; pdb.set_trace()
    for row in rows_iter:
        balance = account_sign * row.balance
        if (prev_balance + row.amount) != balance:
            return False
        prev_balance = balance
    return True
