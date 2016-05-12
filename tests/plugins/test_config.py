"""Unit tests for beansoup.plugins.config module."""

import pytest
import re

from beansoup.plugins import config


def test_error():
    parser = config.ArgumentParser()
    invalid_option = '--not-an-option'
    
    with pytest.raises(config.ParseError) as excinfo:
        args = parser.parse_args([invalid_option])
    assert 'unrecognized argument' in excinfo.value.message
    assert invalid_option in excinfo.value.message


def test_exit():
    parser = config.ArgumentParser()

    with pytest.raises(config.ParseError) as excinfo:
        args = parser.parse_args(['--help'])
    assert 'usage' in excinfo.value.message


def test_re_type():
    parser = config.ArgumentParser()
    parser.add_argument(
        '--test_re', metavar='REGEX', default=None, type=config.re_type)

    args = parser.parse_args('--test_re \\d'.split())

    assert args.test_re
    assert args.test_re.match('3')
    assert not args.test_re.match('X')

    with pytest.raises(config.ParseError) as excinfo:
        args = parser.parse_args('--test_re [a-'.split())
    assert 'invalid regular expression' in excinfo.value.message
