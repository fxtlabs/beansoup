"""An importer that can pass extracted entries through a chain of filters."""

from beancount.ingest import importer


class Importer(importer.ImporterProtocol):
    """An importer that can pass imported entries through a pipeline of filters.

    This importer forwards all its methods to a chosen importer and when
    extracting entries from a file it filters them through a chain of
    arbitrary filters.
    """
    def __init__(self, importer, *filters):
        """Create a filtered importer given an importer and a list of filters.

        Args:
          importer: A concrete instance of ImporterProtocol, the main importer.
          filters: A list of callables taking a list of entries and returning
            a subset of them.
        """
        self.importer = importer
        self.filters = filters

    def name(self):
        """Forwarded to the main importer."""
        return self.importer.name()

    def identify(self, file):
        """Forwarded to the main importer."""
        return self.importer.identify(file)

    def file_account(self, file):
        """Forwarded to the main importer."""
        return self.importer.file_account(file)

    def file_name(self, file):
        """Forwarded to the main importer."""
        return self.importer.file_name(file)

    def file_date(self, file):
        """Forwarded to the main importer."""
        return self.importer.file_date(file)

    def extract(self, file):
        """Extract the entries using the main importer and then run all
        the filters on them.
        """
        entries = self.importer.extract(file)
        for filter in self.filters:
            entries = filter(entries)
        return entries
