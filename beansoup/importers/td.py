"""Importers for TD Canada Trust."""

import csv
import collections
import datetime
import logging
from os import path
import re

from beancount.core import account_types
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
                 first_day=None, filename_regexp=None, option_map=None):
        """Create a new importer for the given account.

        Args:
          account: An account string, the account to associate to the files.
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
        self.account_types = options.get_account_types(option_map) if option_map else None

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
        records = file.convert(parse)
        date = max(record.date for record in records)
        if self.first_day is not None:
            _, date = period.enclose_date(date, first_day=self.first_day)
        return date

    def extract(self, file):
        """Return extracted entries and errors."""
        records = file.convert(parse)
        new_entries = []
        for record in records:
            number = record.credit if record.credit is not None else -record.debit
            posting = data.Posting(
                self.account,
                amount.Amount(number, self.currency),
                None, None, None, None)
            meta = data.new_metadata(file.name, record.lineno)
            payee = None
            narration = record.description
            entry = data.Transaction(
                meta,
                record.date,
                self.FLAG,
                payee,
                narration,
                None,
                None,
                [posting])
            new_entries.append(entry)
        new_entries = data.sorted(new_entries)

        # Extract balance, but only if the account is in (assets, liabilities)
        account_type = account_types.get_account_type(self.account)
        if (records and
            self.account_types and
            account_type in (self.account_types.assets,
                             self.account_types.liabilities)):
            last_record = records[-1]
            if account_type == self.account_types.assets:
                balance = last_record.balance
            else:
                balance = -last_record.balance
            # The Balance assertion occurs at the beginning of the date,
            # so move it to the following day.
            date = last_record.date + datetime.timedelta(days=1)
            meta = data.new_metadata(file.name, last_record.lineno)
            balance_entry = data.Balance(meta, date, self.account,
                                         amount.Amount(balance, self.currency),
                                         None, None)
            new_entries.append(balance_entry)

        return new_entries


csv.register_dialect('td', delimiter=',', quoting=csv.QUOTE_MINIMAL)

Record = collections.namedtuple('Record',
                                'lineno date description debit credit balance')

def parse_record(record, lineno):
    date = datetime.datetime.strptime(record[0], '%m/%d/%Y').date()
    description = record[1]
    debit = D(record[2]) if record[2] else None
    credit = D(record[3]) if record[3] else None
    balance = D(record[4])
    return Record(lineno, date, description, debit, credit, balance)


def parse(filename):
    """Parse a TD Canada Trust CSV file.

    Args:
      filename: The name of the CSV file to be parsed.
    Results:
      A list of Record objects.
    """
    with open(filename, newline='') as file:
        reader = csv.reader(file, 'td')
        try:
            records = [parse_record(record, reader.line_num) for record in reader]
        except (csv.Error, ValueError) as exc:
            logging.error('{}:{}: {}'.format(filename, reader.line_num, exc))
            records = []

    # We assume the records are in chronological order, but we do not know
    # whether ascending or descending. We need them in ascending order.
    if len(records) > 1:
        first_date = records[0].date
        last_date = records[-1].date
        if first_date < last_date:
            pass
        elif last_date < first_date:
            records.reverse()
        else:
            # This is the hard case
            # FIXME: to be implemented
            pass

    return records
