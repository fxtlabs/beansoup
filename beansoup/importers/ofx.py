"""OFX importers."""

from beancount.ingest.importers import ofx

from beansoup.transactions import TransactionCompleter


class SimpleOFXImporter(ofx.Importer):
    """An OFX importer for banking and credit card accounts.

    This importer is based on `beancount.ingest.importers.ofx.Importer`,
    but it also tries to complete the missing leg of the generated
    transactions by looking at the existing entries for similar
    transactions.
    """
    def __init__(self, acctid_regexp, account, basename=None,
                 balance_type=ofx.BalanceType.DECLARED, existing_entries=None):
        self.existing_entries = existing_entries
        super(SimpleOFXImporter, self).__init__(
            acctid_regexp, account, basename, balance_type)

    def extract(self, file):
        entries = super(SimpleOFXImporter, self).extract(file)
        if entries and self.existing_entries:
            completer = TransactionCompleter(self.existing_entries,
                                             self.account)
            completer.complete_entries(entries)
        return entries
