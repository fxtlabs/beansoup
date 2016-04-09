"""Work in progress. It works, but needs documentation and some cleaning.
"""

import ast
import collections
import datetime
import itertools

from beancount.core import data, flags

from beansoup.utils import dates

__plugins__ = ('clear_transactions',)


def clear_transactions(entries, unused_options_map, config):
    config_obj = ast.literal_eval(config)
    if not isinstance(config_obj, dict):
        raise RuntimeError("Invalid plugin configuration: expecting a dict")

    processor = Processor(
        flag_pending=config_obj.get('flag_pending', False),
        cleared_tag_name=config_obj.get('cleared_tag_name', 'CLEARED'),
        pending_tag_name=config_obj.get('pending_tag_name', 'PENDING'),
        ignored_tag_name=config_obj.get('ignored_tag_name', 'PRE_CLEARED'),
        cleared_link_prefix=config_obj.get('cleared_link_prefix', 'clearing'),
        max_delta_days=config_obj.get('max_delta_days', 5),
        skip_weekends=config_obj.get('skip_weekends', True),
        clearing_account_pairs=config_obj.get('account_pairs', []))
      
    modified_entries = processor.clear_transactions(entries)

    # FIXME: Consider printing the pending entries. Maybe return errors for them.
    
    return ([modified_entries.get(id(entry), entry) for entry in entries], [])


class Processor:
    def __init__(self, flag_pending, cleared_tag_name, pending_tag_name,
                 ignored_tag_name, cleared_link_prefix,
                 max_delta_days, skip_weekends,
                 clearing_account_pairs):
        self.flag_pending = flag_pending
        self.cleared_tag_name = cleared_tag_name
        self.pending_tag_name = pending_tag_name
        self.ignored_tag_name = ignored_tag_name
        self.cleared_link_prefix = cleared_link_prefix
        self.max_delta_days = max_delta_days
        self.skip_weekends = skip_weekends
        self.clearing_accounts = dict(clearing_account_pairs)
        
        self.modified_entries = None
        self.link_count = itertools.count(start=1)

    def clear_transactions(self, entries):
        self.modified_entries = {}
        groups = collections.defaultdict(list)
        for entry in entries:
            if (not isinstance(entry, data.Transaction) or
                    (entry.tags and self.ignored_tag_name in entry.tags)):
                continue
            posting = self.get_txn_clearing_posting(entry)
            if posting:
                groups[posting.account].append(data.TxnPosting(entry, posting))

        for txn_postings in groups.values():
            self.clear_transaction_group(txn_postings)

        return self.modified_entries

    def get_txn_clearing_posting(self, txn):
        # This code implicitly assumes that a transaction can only have
        # one posting to a clearing account
        for posting in txn.postings:
            if posting.account in self.clearing_accounts:
                return posting

    def clear_transaction_group(self, txn_postings):
        # Make sure the transactions are sorted;
        # other plugins could have changed their order
        txn_postings = collections.deque(
            sorted(txn_postings, key=lambda x: data.entry_sortkey(x.txn)))

        while txn_postings:
            txn_posting = txn_postings.popleft()
            if id(txn_posting.txn) in self.modified_entries:
                # This transaction has already been cleared
                continue
            # Look for matching transactions within a maximum time delta
            max_date = self.max_matching_date(txn_posting.txn)
            for txn_posting2 in itertools.takewhile(lambda x: x.txn.date <= max_date, txn_postings):
                if id(txn_posting2.txn) in self.modified_entries:
                    # This transaction has already been cleared
                    continue
                if self.match_txn_postings(txn_posting, txn_posting2):
                    # Found match; link the transactions and tag them as cleared
                    link_name = '{}-{}'.format(self.cleared_link_prefix,
                                               next(self.link_count))
                    txn = txn_posting.txn
                    self.modified_entries[id(txn)] = txn._replace(
                        tags=(txn.tags or set()) | set((self.cleared_tag_name,)),
                        links=(txn.links or set()) | set((link_name,)))
                    txn2 = txn_posting2.txn
                    self.modified_entries[id(txn2)] = txn2._replace(
                        tags=(txn2.tags or set()) | set((self.cleared_tag_name,)),
                        links=(txn2.links or set()) | set((link_name,)))
                    break
            else:
                # No match; mark the transaction as pending
                txn = txn_posting.txn
                self.modified_entries[id(txn)] = txn._replace(
                    flag=flags.FLAG_WARNING if self.flag_pending else txn.flag,
                    tags=(txn.tags or set()) | set((self.pending_tag_name,)))

    def max_matching_date(self, txn):
        if self.skip_weekends:
            return dates.add_biz_days(txn.date, self.max_delta_days)
        return txn.date + datetime.timedelta(days=self.max_delta_days)

    def match_txn_postings(self, txn_posting, txn_posting2):
        # We already know the two transactions are within the max time gap
        # and share a clearing account

        # We can have a match only if the postings to the clearing account
        # on the two transactions balance out to 0
        if txn_posting.posting.units != -txn_posting2.posting.units:
            return False

        # We can have a match only if one and only one of the two transactions
        # has a posting to the main account related to their common clearing
        # account
        main_account = self.clearing_accounts[txn_posting.posting.account]
        num_main_account_postings = len(
            [posting for posting in (txn_posting.txn.postings + txn_posting2.txn.postings) if posting.account == main_account])
        return num_main_account_postings == 1
