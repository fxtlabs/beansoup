"""Work in progress. It works, but needs documentation and some cleaning.
"""

import argparse
import collections
import datetime
import itertools

from beancount.core import data, getters, flags

from beansoup.plugins import config
from beansoup.utils import dates

__plugins__ = ('clear_transactions',)


class AccountPairType:
    def __init__(self, entries):
        self.existing_accounts = getters.get_accounts(entries)

    def __call__(self, string):
        accounts = string.split(',')
        if len(accounts) != 2:
            msg = "invalid account pair: '{}'; expecting clearing and main account names separated by a comma (no spaces)".format(string)
            raise argparse.ArgumentTypeError(msg)
        for account in accounts:
            if account not in self.existing_accounts:
                msg = "account '{}' does not exist".format(account)
                raise argparse.ArgumentTypeError(msg)
        return tuple(accounts)


def clear_transactions(entries, options_map, config_string):
    # Parse plugin config; report errors if any
    parser = config.ArgumentParser(
        prog='beansoup.plugins.clear_transactions',
        description='A plugin that automatically tags cleared and pending transactions.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        add_help=False,
        entries_filename=options_map['filename'])
    parser.add_argument(
        '--flag_pending', action='store_true', default=False,
        help='annotate pending transactions with a {} flag'.format(flags.FLAG_WARNING))
    parser.add_argument(
        '--cleared_tag', metavar='TAG', default='CLEARED',
        help='tag cleared transactions with %(metavar)s')
    parser.add_argument(
        '--pending_tag', metavar='TAG', default='PENDING',
        help='tag pending transactions with %(metavar)s')
    parser.add_argument(
        '--ignored_tag', metavar='TAG', default='PRE_CLEARED',
        help='ignore transactions that have a %(metavar)s tag')
    parser.add_argument(
        '--link_prefix', metavar='PREFIX', default='cleared',
        help='link pairs of cleared transactions with %(metavar)s string followed by increasing count')
    parser.add_argument(
        '--max_days', metavar='N', type=int, default=7,
        help='only pair transactions if they occurred no more than %(metavar)s days apart')
    parser.add_argument(
        '--skip_weekends', action='store_true', default=False,
        help='skip weekends when measuring the time gap between transactions')
    parser.add_argument(
        'account_pairs', metavar='CLEARING_ACCOUNT,MAIN_ACCOUNT', nargs='+',
        type=AccountPairType(entries),
        help='the names of a clearing account and its main account, separated by a comma (no space)')

    try:
        args = parser.parse_args((config_string or '').split())
    except config.ParseError as error:
        return entries, [error]

    processor = Processor(args)

    modified_entries, errors = processor.clear_transactions(entries)

    # FIXME: Consider printing the pending entries. Maybe return errors for them.

    return [modified_entries.get(id(entry), entry) for entry in entries], errors


class Processor:
    def __init__(self, args):
        self.flag_pending = args.flag_pending
        self.cleared_tag_name = args.cleared_tag
        self.pending_tag_name = args.pending_tag
        self.ignored_tag_name = args.ignored_tag
        self.cleared_link_prefix = args.link_prefix
        self.max_delta_days = args.max_days
        self.skip_weekends = args.skip_weekends
        self.clearing_accounts = dict(args.account_pairs)

        self.modified_entries = None
        self.link_count = itertools.count(start=1)

    def clear_transactions(self, entries):
        errors = []
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

        return self.modified_entries, errors

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
