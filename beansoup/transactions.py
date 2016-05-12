"""Utilities to work with beancount.core.data.Transaction objects."""

import datetime
import itertools
from os import path

from beancount.core import data, flags, number


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

    def __init__(self, existing_entries, account, min_score=0.5, max_age=None,
                 interpolated=False):
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
          interpolated: If True, the missing posting will include an
            interpolated amount; otherwise, the amount will be left blank.
        """
        def is_model(entry):
            """A predicate asking whether an entry can be used as a model.

            An entry can be considered a model for incomplete transactions
            if it is a transaction with exactly two postings and it
            involves the main account.
            """
            return (isinstance(entry, data.Transaction) and
                    len(entry.postings) == 2 and
                    any(posting.account == account for posting in entry.postings))

        if max_age:
            min_date = datetime.date.today() - max_age
            entries = itertools.takewhile(lambda entry: entry.date >= min_date,
                                          reversed(existing_entries or []))
        else:
            entries = existing_entries or []
        self.model_txns = [entry for entry in entries if is_model(entry)]
        self.account = account
        self.min_score = min_score
        self.interpolated = interpolated

    def __call__(self, entries):
        """Same as `complete_entries` method."""
        return self.complete_entries(entries)

    def complete_entries(self, entries):
        """Complete the given entries.

        Only transactions with a single posting to the account bound to the
        completer may be modified.

        Args:
          entries: The entries to be completed.
        Returns:
          A list of completed entries
        """
        for entry in entries:
            self.complete_entry(entry)
        return entries

    def complete_entry(self, entry):
        """Complete the given entry.

        This method attempts to complete the entry only if it is a transaction
        with a single posting to the account bound to the completer.
        The entry will be completed only if a suitable model transaction can
        be found.
        If multiple model transactions are found that balance the transaction
        against different account, the missing posting will be flagged for
        review.

        Args:
          entry: The entry to be completed.
        Returns: True is the entry was completed; False, otherwise.
        """
        if (isinstance(entry, data.Transaction) and
                len(entry.postings) == 1 and
                entry.postings[0].account == self.account):
            model_txn, model_accounts = self.find_best_model(entry)
            if model_txn:
                # If past transactions similar to this one were posted against
                # different accounts, flag the posting in the new entry.
                flag = flags.FLAG_WARNING if len(model_accounts) > 1 else None
                # Add the missing posting to balance the transaction
                for posting in model_txn.postings:
                    if posting.account != self.account:
                        units = -entry.postings[0].units if self.interpolated else None
                        missing_posting = data.Posting(
                            posting.account, units, None, None, flag, None)
                        entry.postings.append(missing_posting)
                return True
        return False

    def find_best_model(self, txn):
        """Return the best model for the given incomplete transaction.

        Args:
          txn: A beancount.core.data.Transaction object;
            an incomplete transaction with a single posting.
        Returns:
          A pair of a beancount.core.data.Transaction object and a set of
          account strings; the first part is the model transaction or
          None, if no suitable model could be found; the second part is a
          set of the different accounts used by top-scoring transaction to
          balance the posting to the target account.
        """
        scored_model_txns = [(self.score_model(model_txn, txn), model_txn)
                             for model_txn in self.model_txns]
        # Discard low-score transactions
        scored_model_txns = [(score, model_txn) for score, model_txn in scored_model_txns if score >= self.min_score]
        if scored_model_txns:
            # Sort the scored transaction by descending score and date.
            # The first transaction in the sorted list is the best model.
            scored_model_txns = sorted(scored_model_txns,
                                       key=lambda p: (p[0], p[1].date),
                                       reverse=True)
            # Look at the other top-scoring transaction and count how many
            # different accounts they post to; if they post to more than one
            # account (other than the target account), the model is ambiguous.
            best_score, best_model_txn = scored_model_txns[0]
            top_model_txns = itertools.takewhile(lambda p: p[0] == best_score,
                                                 scored_model_txns)
            accounts = set([posting.account for _, txn in top_model_txns for posting in txn.postings if posting.account != self.account])
            return (best_model_txn, accounts)
        return (None, set())

    def score_model(self, model_txn, txn):
        """Score an existing transaction for its ability to provide a model
        for an incomplete transaction.

        Args:
          model_txn: The transaction to be scored.
          txn: The incomplete transaction.
        Returns:
          A float number representing the score, normalized in [0,1].
        """
        def get_description(txn):
            return ('{} {}'.format(txn.payee or '', txn.narration or '')).strip()

        # If the target transaction does not have a description, there is
        # nothing we can do
        txn_description = get_description(txn)
        n_max = len(txn_description)
        if n_max > 1:
            # Only consider model transactions whose posting to the target
            # account has the same sign as the transaction to be completed
            posting = [p for p in model_txn.postings if p.account == self.account][0]
            if number.same_sign(posting.units.number, txn.postings[0].units.number):
                model_txn_description = get_description(model_txn)
                n_match = len(path.commonprefix(
                    [model_txn_description, txn_description]))
                score = float(n_match) / float(n_max)
                return score
        return 0
