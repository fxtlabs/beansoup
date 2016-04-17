"""A file-only importer."""

import calendar
import datetime
import logging
from os import path
import re

from beancount.ingest import importer

from beansoup.utils import dates


class Importer(importer.ImporterProtocol):
    """A document-filing class for monthly files; it does not import anything.

    This importer only supports bean-identify and bean-file. It does not
    extract any transactions; in fact, it does not even open the file.
    It uses a regular expression to match a filename to an account and to
    a date (interpreted as the last day of a billing period).
    """
    def __init__(self, account, basename=None,
                 first_day=1, filename_regexp=None):
        """Create a new filing importer for the given account.

        Args:
          account: An account string, the account to associate to the files.
          basename: An optional string, the name of the new files.
          filename_regexp: A regular expression string used to match the
            basename (no path) of the target file. This regexp should include
            capturing groups for `year`, `month`, and (optional) `day` of
            the end of the period covered by the file; if `day` is
            missing, the `first_day` argument will be used to compute the
            end date.
            Example: '^Statement_(?P<month>\w{3}) (?P<year>\d{4}).pdf$'
          first_day: An int in [1,28]; the first day of the billing period.
        """
        self.filename_re = re.compile(filename_regexp or self.filename_regexp)
        self.account = account
        self.basename = basename
        self.first_day = first_day

    def name(self):
        """Include the filing account in the name."""
        return '{}: "{}"'.format(super().name(), self.file_account(None))

    def identify(self, file):
        """Identify whether the file can be processed by this importer."""
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
        matches = self.filename_re.match(path.basename(file.name))
        if matches:
            groups = matches.groupdict()
            today = datetime.date.today()
            year = int(groups['year']) if 'year' in groups else today.year
            month = dates.month_number(groups.get('month')) or today.month
            if 'day' in groups:
                # The filename fully specifies the document date
                day = int(groups['day'])
                date = datetime.date(year, month, day)
            else:
                # Use the first day of the billing cycle to compute the
                # last day of the period for the given year and month
                if self.first_day > 1:
                    date = (datetime.date(year, month, self.first_day) -
                            datetime.timedelta(days=1))
                else:
                    _, month_last_day = calendar.monthrange(year, month)
                    date = datetime.date(year, month, day)
            return date

    def extract(self, file):
        """Do not attempt to extract any transactions from the file."""
        logging.warning(
            "Cannot extract entries from file '{}'. "
            "Please use a proper importer and data format".format(file.name))
        return []
