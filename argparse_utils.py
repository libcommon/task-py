## -*- coding: UTF-8 -*-
## argparse_utils.py
##
## Copyright (c) 2019 libcommon
##
## Permission is hereby granted, free of charge, to any person obtaining a copy
## of this software and associated documentation files (the "Software"), to deal
## in the Software without restriction, including without limitation the rights
## to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
## copies of the Software, and to permit persons to whom the Software is
## furnished to do so, subject to the following conditions:
##
## The above copyright notice and this permission notice shall be included in all
## copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
## OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
## SOFTWARE.


from argparse import _SubParsersAction, ArgumentParser
from typing import Optional


__author__ = "libcommon"


def has_subcommands(parser: ArgumentParser) -> bool:
    """Check whether parser has subcommands defined."""
    return parser._subparsers is not None and len(parser._subparsers._actions) > 1

def get_subcommands(parser: ArgumentParser) -> Optional[_SubParsersAction]:
    """Retrieve subcommands from parser if defined."""
    if not has_subcommands(parser):
        return None
    subcommands = parser._subparsers._actions[1]    # type: ignore
    if not isinstance(subcommands, _SubParsersAction):
        return None
    return subcommands

def has_subcommand(parser: ArgumentParser, subcommand: str) -> bool:
    """Check whether parser has specific subcommand defined."""
    subcommands = get_subcommands(parser)
    return subcommands is not None and subcommand in subcommands.choices

def get_subcommand(parser: ArgumentParser, subcommand: str) -> Optional[ArgumentParser]:
    """Retrieve subcommand from parser if defined."""
    subcommands = get_subcommands(parser)
    if subcommands is None or subcommand not in subcommands.choices:
        return None
    return subcommands.choices.get(subcommand)

def add_subcommand(parser: ArgumentParser,
                   subcommand: str, description: Optional[str]) -> ArgumentParser:
    """Add subcommand with description to parser, creating subcommands if not defined already."""
    subcommands = get_subcommands(parser)
    if subcommands is None:
        subcommands = parser.add_subparsers()
    if subcommand not in subcommands.choices:
        subcommand_parser: ArgumentParser = subcommands.add_parser(subcommand, description=description)
    else:
        subcommand_parser = subcommands.choices.get(subcommand)     # type: ignore
        if bool(description) and not bool(subcommand_parser.description):
            subcommand_parser.description = description
    return subcommand_parser
