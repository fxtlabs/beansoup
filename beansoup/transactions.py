# -*- coding: utf-8 -*-

from beancount.core.data import Transaction, create_simple_posting
from beancount.core.number import same_sign
from datetime import date
from itertools import takewhile
from os.path import commonprefix


class TransactionCompleter(object):

    def __init__(self, entries, account, min_score=0.5, max_age=None):
        def is_model(entry):
            return (isinstance(entry, Transaction) and
                    len(entry.postings) == 2 and
                    any(posting.account == account for posting in entry.postings))

        entries = reversed(entries)
        if max_age:
            min_date = date.today() - max_age
            entries = takewhile(lambda entry: entry.date >= min_date, entries)
        self.model_txns = list(filter(is_model, entries))
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
                                              -posting.units.number,
                                              posting.units.currency)
                return True
        return False
    
    def find_best_model(self, txn):
        scored_model_txns = [(self.score_model(model_txn, txn), model_txn) for model_txn in self.model_txns]
        if scored_model_txns:
            # Given the same score, the most recent transaction wins
            score, model_txn = max(scored_model_txns, key=lambda p: (p[0], p[1].date))
            if score >= self.min_score:
                return model_txn

    def score_model(self, model_txn, txn):
        # If the target transaction does not have a narration, there is
        # nothing we can do
        n = len(txn.narration)
        if n > 0:
            # Only consider model transactions whose posting to the target
            # account has the same sign as the transaction to be completed
            posting = [p for p in model_txn.postings if p.account == self.account][0]
            if same_sign(posting.units.number, txn.postings[0].units.number):
                c1 = len(commonprefix([model_txn.payee, txn.narration])) if model_txn.payee else 0
                c2 = len(commonprefix([model_txn.narration, txn.narration])) if model_txn.narration else 0
                score = max(c1, c2) / float(n)
                return score
        return 0
