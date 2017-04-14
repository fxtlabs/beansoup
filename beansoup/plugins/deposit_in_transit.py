"""Work in progress. It works, but needs documentation and some cleaning.

A plugin that automatically ties split deposit-in-transit transactions.

usage: beansoup.plugins.deposit_in_transit [--dit_component NAME]
                                           [--auto_open] [--same_day_merge]
                                           [--flag_pending]
                                           [--cleared_tag TAG]
                                           [--pending_tag TAG]
                                           [--ignored_tag TAG]
                                           [--link_prefix PREFIX]
                                           [--skip_re REGEX]

optional arguments:
  --dit_component NAME  use NAME as the component name distinguishing deposit-
                        in-transit accounts (default: DIT)
  --auto_open           automatically open deposit-in-transit accounts
                        (default: False)
  --same_day_merge      merge same-day transactions with matching deposit-in-
                        transit postings (default: False)
  --flag_pending        annotate pending transactions with a ! flag (default:
                        False)
  --cleared_tag TAG     tag cleared transactions with TAG (default: DEPOSITED)
  --pending_tag TAG     tag pending transactions with TAG (default: IN-
                        TRANSIT)
  --ignored_tag TAG     ignore transactions that have a TAG tag (default:
                        IGNORED)
  --link_prefix PREFIX  link pairs of cleared transactions with PREFIX string
                        followed by increasing count; otherwise it uses UUIDs
                        (default: None)
  --skip_re REGEX       disable plugin if REGEX matches any sys.argv (default:
                        None)
"""

import argparse
import collections
import itertools
import sys

from beancount.core import data, flags, getters
from beancount.core.account import has_component

from beansoup.plugins import config
from beansoup.utils import links

__plugins__ = ('plugin',)


DITError = collections.namedtuple('DITError', 'source message entry')


def plugin(entries, options_map, config_string):
    # Parse plugin config; report errors if any
    parser = config.ArgumentParser(
        prog=__name__,
        description='A plugin that automatically ties split deposit-in-transit transactions.',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        add_help=False,
        entries_filename=options_map['filename'])
    parser.add_argument(
        '--dit_component', metavar='NAME', default='DIT',
        help='use %(metavar)s as the component name distinguishing deposit-in-transit accounts')
    parser.add_argument(
        '--auto_open', action='store_true', default=False,
        help='automatically open deposit-in-transit accounts')
    parser.add_argument(
        '--same_day_merge', action='store_true', default=False,
        help='merge same-day transactions with matching deposit-in-transit postings')
    parser.add_argument(
        '--flag_pending', action='store_true', default=False,
        help='annotate pending transactions with a {} flag'.format(flags.FLAG_WARNING))
    parser.add_argument(
        '--cleared_tag', metavar='TAG', default='DEPOSITED',
        help='tag cleared transactions with %(metavar)s')
    parser.add_argument(
        '--pending_tag', metavar='TAG', default='IN-TRANSIT',
        help='tag pending transactions with %(metavar)s')
    parser.add_argument(
        '--ignored_tag', metavar='TAG', default='IGNORED',
        help='ignore transactions that have a %(metavar)s tag')
    parser.add_argument(
        '--link_prefix', metavar='PREFIX', default=None,
        help='link pairs of cleared transactions with %(metavar)s string followed by increasing count; otherwise it uses UUIDs')
    parser.add_argument(
        '--skip_re', metavar='REGEX', default=None, type=config.re_type,
        help='disable plugin if %(metavar)s matches any sys.argv')

    try:
        args = parser.parse_args((config_string or '').split())
    except config.ParseError as error:
        return entries, [error]

    # If the plugin was called with the --skip_re option and the given
    # regular expression matches any of the arguments in sys.argv,
    # do not run the plugin and return the original entries instead.
    if args.skip_re and any(args.skip_re.match(arg) for arg in sys.argv):
        return entries, []

    unchanged_entries, new_entries, errors = process_entries(entries, args)

    # FIXME: Consider printing the pending entries. Maybe return errors for them.

    return sorted(unchanged_entries + new_entries, key=data.entry_sortkey), errors


def process_entries(entries, args):
    new_entries = []

    if args.auto_open:
        new_entries.extend(open_dit_accounts(entries, args.dit_component))

    # Find all DIT transactions to be processed; their original entries
    # will be replaced by new ones
    dits, unchanged_entries, errors = split_entries(
        entries,
        dit_component=args.dit_component,
        ignored_tag=args.ignored_tag)

    pairs, singletons, pairing_errors = pair_dits(
        dits, dit_component=args.dit_component)
    errors.extend(pairing_errors)

    cleared_links = links.count(args.link_prefix)
    for pair in pairs:
        new_entries.extend(process_pair(
            pair,
            cleared_tag=args.cleared_tag,
            cleared_links=cleared_links,
            same_day_merge=args.same_day_merge))

    new_entries.extend(
        [process_singleton(singleton,
                           flag_pending=args.flag_pending,
                           pending_tag=args.pending_tag) for singleton in singletons])

    return unchanged_entries, new_entries, errors


def open_dit_accounts(entries, dit_component):
    """
    Minimally adapted from beancount.plugins.auto_accounts.
    """
    opened_accounts = {entry.account
                       for entry in entries
                       if isinstance(entry, data.Open)}

    new_entries = []
    accounts_first, _ = getters.get_accounts_use_map(entries)
    for index, (account, date_first_used) in enumerate(sorted(accounts_first.items())):
        if ((account not in opened_accounts) and
                has_component(account, dit_component)):
            meta = data.new_metadata(__name__, index)
            new_entry = data.Open(meta, date_first_used, account, None, None)
            new_entries.append(new_entry)

    return new_entries


def split_entries(entries, dit_component, ignored_tag):
    dits, unchanged_entries, errors = [], [], []
    for entry in entries:
        if (isinstance(entry, data.Transaction) and
            not (entry.tags and ignored_tag in entry.tags)):
            dit_postings = [posting for posting in entry.postings if has_component(posting.account, dit_component)]
            num_dit_postings = len(dit_postings)
        else:
            num_dit_postings = 0
        if num_dit_postings == 0:
            unchanged_entries.append(entry)
        else:
            dits.append(data.TxnPosting(entry, dit_postings[0]))
            if num_dit_postings > 1:
                errors.append(DITError(
                    entry.meta,
                    "(deposit_in_transit) Found entry with multiple postings to DIT accounts; "
                    "only processing posting to {} account".format(
                        dit_postings[0].account),
                    entry))
    return dits, unchanged_entries, errors


def pair_dits(dits, dit_component):
    # A map from amounts to all DIT postings (as a TxnPosting) sharing
    # that amount
    units_map = collections.defaultdict(list)
    for dit in dits:
        units_map[dit.posting.units].append(dit)

    pairs, singletons, errors = [], [], []
    skip_ids = set()
    for dit in dits:
        if id(dit.txn) in skip_ids:
            continue
        units_map[dit.posting.units].remove(dit)
        dit2 = match_dit(dit, units_map.get(-dit.posting.units), dit_component)
        if dit2:
            # Found matching DIT transaction
            pairs.append((dit, dit2))
            skip_ids |= {id(dit2.txn)}
            units_map[dit2.posting.units].remove(dit2)
        else:
            singletons.append(dit)

    return pairs, singletons, errors


def match_dit(dit, candidate_dits, dit_component):
    # FIXME: check DIT- and base-accounts match
    return candidate_dits[0] if candidate_dits else None


def process_pair(pair, cleared_tag, cleared_links, same_day_merge):
    def tag_and_link(entry, cleared_link):
        tags = (entry.tags or set()) | {cleared_tag}
        links = (entry.links or set()) | {cleared_link}
        return entry._replace(tags=tags, links=links)
    
    def xform_posting(posting):
        return data.Posting(posting.account,
                            -posting.units,
                            None, None, None, None)

    # The first in the pair should be the sender; the second, the receiver.
    if pair[0].posting.units < pair[1].posting.units:
        pair = (pair[1], pair[0])

    date = max(pair[0].txn.date, pair[1].txn.date)
    if pair[0].txn.narration == pair[1].txn.narration:
        narration = pair[0].txn.narration
    else:
        narration = '{} / {}'.format(pair[0].txn.narration, pair[1].txn.narration)
    if pair[0].txn.payee is None:
        payee = pair[1].txn.payee
    elif pair[1].txn.payee is None:
        payee = pair[0].txn.payee
    elif pair[0].txn.payee == pair[1].txn.payee:
        payee = pair[0].txn.payee
    else:
        payee = '{} / {}'.format(pair[0].txn.payee, pair[1].txn.payee)

    if same_day_merge and is_pair_mergeable(pair):
        # Merge the two transactions
        meta = pair[0].txn.meta
        flag = pair[0].txn.flag
        tags = ((pair[0].txn.tags or set()) |
                (pair[1].txn.tags or set()) |
                {cleared_tag})
        links = ((pair[0].txn.links or set()) |
                 (pair[1].txn.links or set())) or data.EMPTY_SET
        postings = ([posting for posting in pair[0].txn.postings if posting is not pair[0].posting] +
                    [posting for posting in pair[1].txn.postings if posting is not pair[1].posting])
        new_entry = data.Transaction(
            meta,
            date,
            flag,
            payee,
            narration,
            tags,
            links,
            postings)
        return (new_entry, )

    # Make sure the connecting entry will be shown between the two existing
    # ones when looking at the list of entries for their common link
    lineno = int((pair[0].txn.meta.get('lineno', 0) +
                  pair[1].txn.meta.get('lineno', 0)) / 2)
    meta = data.new_metadata(__name__, lineno)
    cleared_link = next(cleared_links)
    new_entry = data.Transaction(
        meta,
        date,
        flags.FLAG_OKAY,
        payee,
        narration,
        {cleared_tag},
        {cleared_link},        
        [xform_posting(pair[0].posting), xform_posting(pair[1].posting)])

    return (tag_and_link(pair[0].txn, cleared_link),
            tag_and_link(pair[1].txn, cleared_link),
            new_entry)


def is_pair_mergeable(pair):
    if pair[0].txn.flag != pair[1].txn.flag:
        return False

    if pair[0].txn.date != pair[1].txn.date:
        return False

    if (pair[0].posting.cost or pair[0].posting.price or
        pair[1].posting.cost or pair[1].posting.price):
        return False

    return True

    
def process_singleton(singleton, flag_pending, pending_tag):
    entry = singleton.txn
    flag = flags.FLAG_WARNING if flag_pending else entry.flag
    tags = (entry.tags or set()) | {pending_tag}
    return entry._replace(flag=flag, tags=tags)
