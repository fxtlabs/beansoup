"""Work in progress. It works, but needs documentation and some cleaning.
"""

import argparse
import collections
import itertools

from beancount.core import data, flags
from beancount.core.account import has_component

from beansoup.plugins import config

__plugins__ = ('plugin',)


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
        help='Use %(metavar)s as the component name distinguishing deposit-in-transit accounts')
    parser.add_argument(
        '--same_day_merge', action='store_true', default=False,
        help='merge same-day transactions with matching deposit-in-transit postings')
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

    try:
        args = parser.parse_args((config_string or '').split())
    except config.ParseError as error:
        return entries, [error]

    unchanged_entries, new_entries, errors = process_entries(entries, args)

    # FIXME: Consider printing the pending entries. Maybe return errors for them.

    return unchanged_entries + new_entries, errors


def process_entries(entries, args):
    # Find all DIT transactions to be processed; their original entries
    # will be replaced by new ones
    dits, unchanged_entries, errors = split_entries(
        entries,
        dit_component=args.dit_component,
        ignored_tag=args.ignored_tag)

    pairs, singletons, pairing_errors = pair_dits(
        dits, dit_component=args.dit_component)
    errors.extend(pairing_errors)

    new_entries = []
    cleared_links = enumerate_links(args.link_prefix)
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
                # FIXME: output error
                pass
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
                 (pair[1].txn.links or set())) or None
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


def enumerate_links(link_prefix):
    count = 1
    while True:
        yield '{}-{}'.format(link_prefix, count)
        count += 1
