"""Utilities for working with links."""

import uuid


def count(link_prefix=None, start=1):
    """A generator of unique link names.

    Args:
      link_prefix (Optional[str]): If a string, link names will be of
        the form link_prefix-#; otherwise, they will be UUIDs.
      start (int): The start of the number sequence when used with
        a link prefix.

    Yields:
      str: the next link name in the sequence.
    """
    if link_prefix:
        num = start
        while True:
            yield '{}-{}'.format(link_prefix, num)
            num += 1
    else:
        while True:
            yield str(uuid.uuid4())
