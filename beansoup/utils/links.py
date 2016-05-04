"""Utilities for working with links."""

import uuid


def count(link_prefix=None, start=1):
    """An iterator that returns unique link names.

    Args:
      link_prefix: A string or None. If the former, link names will be of
        the form link_prefix-#; otherwise, they will be UUIDs.
      start: An integer; the start of the number sequence when used with
        a link prefix.
    Returns:
      An iterator that returns unique link names as strings.
    """
    if link_prefix:
        num = start
        while True:
            yield '{}-{}'.format(link_prefix, num)
            num += 1
    else:
        while True:
            yield str(uuid.uuid4())
