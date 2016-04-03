"""Importers for American Express statements."""

import calendar

from beansoup.importers import filing


class PdfFilingImporter(filing.Importer):
    """A filing importer for American Express PDF monthly statements."""
    filename_regexp = ('^Statement_(?P<month>%s) (?P<year>\d{4}).pdf$' %
                       '|'.join(calendar.month_abbr[1:]))
