"""Importers for TD Canada Trust."""

import csv
import collections
import datetime
import logging
from os import path
import re

from beancount.core import amount
from beancount.core import data
from beancount.core.number import D
from beancount.ingest import importer

from beansoup.utils import period


class Importer(importer.ImporterProtocol):
    """An importer for TD Canada Trust CSV statements.

    Unfortunately, these CSV files do not contain any information to easily
    identify the account; for this reason, this importer relies on the name
    of the file to associate it to a particular account.
    """
    def __init__(self, account, currency='CAD', basename=None,
                 first_day=None, filename_regexp=None):
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

        # FIXME: try to extract the balance too

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
            return [parse_record(record, reader.line_num) for record in reader]
        except (csv.Error, ValueError) as exc:
            logging.error('{}:{}: {}'.format(filename, reader.line_num, exc))
