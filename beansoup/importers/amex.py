"""Importers for American Express statements."""

import calendar
import datetime
import logging
from os import path
import re

from beancount.ingest import importer


class PdfFiler(importer.ImporterProtocol):
    """A limited importer for PDF-format American Express monthly statements.

    This importer is really only a filer. It identifies American Express
    monthly statements based exclusively on the file name.
    It is not capable of extracting any transactions, but it can be used
    to identify and file these monthly statements.

    The expected file name follows the pattern
    'Statement_MONTHABBR YEAR.pdf'
    Where MONTHABBR is a 3-character abbreviation of a month, starting with
    an uppercase letter (e.g. Jan) and YEAR is a 4-digit year.
    """
    months = dict((name, i) for i, name in enumerate(calendar.month_abbr))
    file_name_re = re.compile(
        '^Statement_(?P<month>%s) (?P<year>\d{4}).pdf$' % '|'.join(
            calendar.month_abbr[1:]))

    def __init__(self, account, basename=None, first_day=1, closed=False):
        """Create a new filer for the given account.

        Args:
          account: An account string, the account to associate to the statements.
          basename: An optional string, the name of the new files.
          first_day: An int in [1,28]; the first day of the billing period.
          closed: A Boolean; if True, the new files will start with
            the date of the last day of the billing period; otherwise, they
            will start with the date of the following day.
        """
        self.account = account
        self.basename = basename
        self.first_day = first_day
        self.closed = closed

    def name(self):
        """Include the filing account in the name."""
        return '{}: "{}"'.format(super().name(), self.file_account(None))

    def identify(self, file):
        """Identify whether the file can be processed by this importer."""
        # Match for a compatible MIME type.
        if (file.mimetype() != 'application/pdf' and
            file.mimetype() != 'application/x-pdf'):
            return False

        # Match the file name.
        return self.file_name_re.match(path.basename(file.name))

    def file_account(self, _):
        """Return the account associated with the file"""
        return self.account

    def file_name(self, file):
        """Return the optional renamed account file name."""
        if self.basename:
            return self.basename + path.splitext(file.name)[1]

    def file_date(self, file):
        """Return the filing date for the file."""
        matches = self.file_name_re.match(path.basename(file.name))
        year = int(matches.group('year'))
        month = self.months[matches.group('month')]
        date = datetime.date(year, month, self.first_day)
        if self.closed:
            date -= datetime.timedelta(days=1)
        return date

    def extract(self, file):
        """Do not attempt to extract any transactions from the file."""
        logging.warning(
            "Cannot extract from PDF file '{}'. "
            "Please use a proper importer and data format".format(file.name))
        return []
