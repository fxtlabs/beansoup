"""Utilities to facilitate testing."""

import functools
import tempfile
import textwrap

from beancount.ingest import importer


def docfile(*args, **kwargs):
    """A decorator that creates a temporary file from the function's docstring.

    This is actually a decorator builder that returns a decorator that
    writes the function's docstring to a temporary file and calls the
    decorated function with the temporary filename.  This is
    useful for writing tests.

    Args:
      Any argument accepted by `tempfile.NamedTemporaryFile`.
    Returns:
      A decorator.
    """
    def _docfile(function):
        @functools.wraps(function)
        def new_function(self):
            with tempfile.NamedTemporaryFile(*args, **kwargs) as f:
                f.write(textwrap.dedent(function.__doc__))
                f.flush()
                return function(self, f.name)
        new_function.__doc__ = None
        return new_function
    return _docfile


class ConstImporter(importer.ImporterProtocol):
    """
    A helper importer whose extract method simply returns the entries
    passed to its constructor.
    """
    def __init__(self, entries, account):
        self.entries = entries
        self.account = account

    def identify(self, _):
        return True

    def file_account(self, _):
        return self.account

    def file_date(self, _):
        if self.entries:
            return max([entry.date for entry in self.entries])

    def extract(self, _):
        return self.entries
