"""This plugin sorts document directives after other entries at the same date.
"""
from beancount.core import data

__plugins__ = ('sort_docs',)


def sort_docs(entries, unused_options_map):
    """Return the entries unchanged, but modifies the sort order.

    When entries are loaded, they are sorted both before and after
    running any plugins. The sort order is controlled by
    beancount.core.data.SORT_ORDER, a dict mapping directive classes
    to ints. This function changes the mapping to sort directives
    as follows:
    open < balance < other < document < close.

    Args:
      entries: A list of directives.
    Returns:
      The entries unchanged and no errors.
    """
    data.SORT_ORDER = {
        data.Open: -2,
        data.Balance: -1,
        data.Document:1,
        data.Close: 2}
    return entries, []
