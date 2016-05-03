"""Utilities to help parse a plugin configuration string.
"""

import argparse
import re

from beancount.core import data


class ParseError(Exception):
    def __init__(self, source, message):
        self.source = source
        self.message = message
        self.entry = None


class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        entries_filename = kwargs.pop('entries_filename', '<config>')
        self.source = data.new_metadata(entries_filename, 0)
        super(ArgumentParser, self).__init__(*args, **kwargs)

    def error(self, message):
        full_message = '{}\n\n{}'.format(message, self.format_help())
        raise ParseError(self.source, full_message)

    def exit(self, status=0, message=None):
        self.error(message)


def re_type(string):
    """Argument type for regular expressions.

    It returns a compiled regular expression if string is not empty;
    None, otherwise.  It raises argparse.ArgumentTypeError if the
    string is not a valid regular expression.
    """
    if string:
        try:
            string_re = re.compile(string)
        except re.error:
            msg = "invalid regular expression: '{}'".format(string)
            raise argparse.ArgumentTypeError(msg)
        return string_re
