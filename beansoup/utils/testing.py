"""Utilities to facilitate testing."""

import functools
import tempfile
import textwrap


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
