"""Work in progress. It works, but needs documentation and some cleaning.
"""

import argparse
import collections

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
    for count, pair in enumerate(pairs, start=1):
        cleared_link = '{}-{}'.format(args.link_prefix, count)
        new_entries.extend(process_pair(
            pair, cleared_tag=args.cleared_tag, cleared_link=cleared_link))

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


def process_pair(pair, cleared_tag, cleared_link):
    def tag_and_link(entry):
        tags = (entry.tags or set()) | {cleared_tag}
        links = (entry.links or set()) | {cleared_link}
        return entry._replace(tags=tags, links=links)
    
    def xform_posting(posting):
        return data.Posting(posting.account,
                            -posting.units,
                            None, None, None, None)

    meta = data.new_metadata(__name__, 0)
    date = max(pair[0].txn.date, pair[1].txn.date)
    payee = None
    narration = '{} / {}'.format(pair[0].txn.narration, pair[1].txn.narration)
    new_entry = data.Transaction(
        meta,
        date,
        flags.FLAG_OKAY,
        payee,
        narration,
        {cleared_tag},
        {cleared_link},        
        [xform_posting(pair[0].posting), xform_posting(pair[1].posting)])

    return (tag_and_link(pair[0].txn), tag_and_link(pair[1].txn), new_entry)


def process_singleton(singleton, flag_pending, pending_tag):
    entry = singleton.txn
    flag = flags.FLAG_WARNING if flag_pending else entry.flag
    tags = (entry.tags or set()) | {pending_tag}
    return entry._replace(flag=flag, tags=tags)
