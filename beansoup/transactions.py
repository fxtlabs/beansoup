"""Utilities to work with beancount.core.data.Transaction objects."""

from datetime import date
from itertools import takewhile
from os.path import commonprefix

from beancount.core.data import Transaction, create_simple_posting
from beancount.core.number import same_sign


class TransactionCompleter:
    """A class capable of completing partial transactions.

    Importers typically generate incomplete transactions with a single
    posting to the main account related to the imported data. This class
    attempts to complete those transaction by adding a second posting to
    an account chosen based on the existing transaction history for the
    main account.

    It looks for existing transactions that have exactly two postings
    and where one of the two postings is to the main account. It scores
    each of these transactions based on the similarity of its payee and
    narration fields to the narration field of the incomplete
    transaction and selects the one with the highest score as a model to
    fill in the missing posting of the incomplete transaction. Equal
    scores are broken by selecting the most recent transaction.
    """

    def __init__(self, existing_entries, account, min_score=0.5, max_age=None):
        """Initialization.

        Args:
          existing_entries: The existing entries, ordered by increasing date.
          account: The main account of the incomplete transactions
            (i.e. the account of their only posting).
          min_score: The minimum score an existing transaction must
            have to be used as a model for an incomplete transaction.
          max_age: A datetime.timedelta object giving the maximum age
            (measure from datetime.date.today()) a transaction can
            have in order to be used as a model to fill in an incomplete
            transaction.
        """
        def is_model(entry):
            """A predicate asking whether an entry can be used as a model.

            An entry can be considered a model for incomplete transactions
            if it is a transaction with exactly two postings and it
            involves the main account.
            """
            return (isinstance(entry, Transaction) and
                    len(entry.postings) == 2 and
                    any(posting.account == account for posting in entry.postings))

        if max_age:
            min_date = date.today() - max_age
            entries = takewhile(lambda entry: entry.date >= min_date,
                                reversed(existing_entries or []))
        else:
            entries = existing_entries or []
        self.model_txns = [entry for entry in entries if is_model(entry)]
        self.account = account
        self.min_score = min_score

    def complete_entries(self, entries):
        """Complete the given entries.

        Only transactions with a single posting to the account bound to the
        completer may be modified.

        Args:
          entries: The entries to be completed.
        Returns:
          None
        """
        for entry in entries:
            self.complete_entry(entry)

    def complete_entry(self, entry):
        """Complete the given entry.

        This method attempts to complete the entry only if it is a transaction
        with a single posting to the account bound to the completer.
        The entry will be completed only if a suitable model transaction can
        be found.

        Args:
          entry: The entry to be completed.
        Returns: True is the entry was completed; False, otherwise.
        """
        if (isinstance(entry, Transaction) and
                len(entry.postings) == 1 and
                entry.postings[0].account == self.account):
            model_txn = self.find_best_model(entry)
            if model_txn:
                # Add the missing posting to balance the transaction
                for posting in model_txn.postings:
                    if posting.account != self.account:
                        create_simple_posting(entry,
                                              posting.account,
                                              -entry.postings[0].units.number,
                                              entry.postings[0].units.currency)
                return True
        return False

    def find_best_model(self, txn):
        """Return the best model for the given incomplete transaction.

        Args:
          txn: A beancount.core.data.Transaction object;
            an incomplete transaction with a single posting.
        Returns:
          A beancount.core.data.Transaction object to be used as a model or
          None, if no suitable model could be found.
        """
        scored_model_txns = [(self.score_model(model_txn, txn), model_txn)
                             for model_txn in self.model_txns]
        if scored_model_txns:
            # Given the same score, the most recent transaction wins
            score, model_txn = max(scored_model_txns, key=lambda p: (p[0], p[1].date))
            if score >= self.min_score:
                return model_txn

    def score_model(self, model_txn, txn):
        """Score an existing transaction for its ability to provide a model
        for an incomplete transaction.

        Args:
          model_txn: The transaction to be scored.
          txn: The incomplete transaction.
        Returns:
          A float number representing the score, normalized in [0,1].
        """
        # If the target transaction does not have a narration, there is
        # nothing we can do
        n_max = len(txn.narration)
        if n_max > 0:
            # Only consider model transactions whose posting to the target
            # account has the same sign as the transaction to be completed
            posting = [p for p in model_txn.postings if p.account == self.account][0]
            if same_sign(posting.units.number, txn.postings[0].units.number):
                if model_txn.payee:
                    n_payee = len(commonprefix([model_txn.payee, txn.narration]))
                else:
                    n_payee = 0
                if model_txn.narration:
                    n_narration = len(commonprefix([model_txn.narration, txn.narration]))
                else:
                    n_narration = 0
                score = max(n_payee, n_narration) / float(n_max)
                return score
        return 0
