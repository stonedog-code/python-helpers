"""Options that come from the command line, or from a question if they didn't.

Describe each option once and this builds the `--help` and does the asking:

    from python_helpers.args import Option, YES_NO, build_parser, collect

    OPTIONS = [
        Option("server", "server to deploy to", default="pp4435"),
        Option("confirm", "ask before deploying", kind=YES_NO, default=True),
    ]

    parser = build_parser(OPTIONS, description="Deploy the thing.")
    values = collect(OPTIONS, parser.parse_args())
    #  ./deploy.py --server pp9000   ->  asks only about `confirm`
    #  ./deploy.py                   ->  asks about both

The point is that the two halves cannot drift. Writing `add_argument` in one
place and `args.x or ask(...)` in another means every new option is two edits,
and the failure when you make only one of them is silent: the flag parses
fine and is then quietly ignored.
"""

import argparse

from .ask import ask, ask_yes_no

#: A value. Passed as ``--name VALUE``; asked for with `ask` if it wasn't.
TEXT = "text"

#: A bool. Passed as ``--name yes|no``; asked for with `ask_yes_no` if it
#: wasn't. Spelled yes/no rather than as a bare switch because a switch can
#: only turn something on — there would be no way to say "no" on the command
#: line to an option whose default is yes.
YES_NO = "yes_no"

#: A switch, on when present. Never asked about: a flag like ``--dry-run`` is
#: a thing you either reached for or didn't, and prompting for it every run
#: would be asking a question whose answer is already "no".
FLAG = "flag"

KINDS = (TEXT, YES_NO, FLAG)


class Option:
    """One option: how it parses, how it is asked for, and what it defaults to.

    `name` is the Python-side name (``num_parallel``); the command-line flag is
    derived from it (``--num-parallel``), so the two can never disagree.

    `require_value` may be a bool, or a callable taking the values collected so
    far and returning one. The callable form is for an option that is only
    mandatory in some runs — a record id that matters when you are recording
    and is irrelevant when you are not. Options are collected in list order, so
    the callable sees every answer given before it.
    """

    def __init__(
        self,
        name,
        help="",
        default=None,
        kind=TEXT,
        prompt=None,
        metavar=None,
        choices=None,
        require_value=False,
    ):
        if kind not in KINDS:
            raise ValueError(f"unknown kind {kind!r}; expected one of {KINDS}")

        # A default means something different per kind, so normalise it here
        # rather than letting a nonsensical one reach the prompt helpers and
        # fail there — a KeyError raised inside `ask_yes_no` names neither the
        # option nor the mistake.
        if kind == TEXT and default is None:
            default = ""
        elif kind == YES_NO and default not in (True, False, None):
            raise ValueError(
                f"{name}: a {YES_NO} default must be True, False, or None "
                f"(no default), not {default!r}"
            )

        self.name = name
        self.help = help
        self.default = default
        self.kind = kind
        self.prompt = prompt
        self.metavar = metavar
        self.choices = choices
        self.require_value = require_value

    @property
    def flag(self):
        """The command-line spelling: ``num_parallel`` -> ``--num-parallel``."""
        return "--" + self.name.replace("_", "-")

    @property
    def question(self):
        """The prompt text, defaulting to a readable form of the name."""
        return self.prompt or self.name.replace("_", " ").capitalize()

    def is_required(self, values):
        """Whether an empty answer should be refused, given what came before."""
        if callable(self.require_value):
            return bool(self.require_value(values))
        return bool(self.require_value)


def build_parser(options, prog=None, description=None, epilog=None):
    """Build the ArgumentParser for `options`."""
    parser = argparse.ArgumentParser(
        prog=prog,
        description=description,
        epilog=epilog,
        # Keep the epilog's line breaks; the default formatter reflows an
        # examples block into one unreadable paragraph.
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    for option in options:
        if option.kind == FLAG:
            parser.add_argument(option.flag, action="store_true", help=option.help)
        elif option.kind == YES_NO:
            parser.add_argument(option.flag, choices=["yes", "no"], help=option.help)
        else:
            parser.add_argument(
                option.flag,
                metavar=option.metavar or option.name.upper(),
                choices=option.choices,
                help=option.help,
            )
    return parser
    # Note what is NOT set: `default`. Every option parses to None when it is
    # absent, and None is the whole mechanism — it is what distinguishes "not
    # passed, so ask" from "passed a value". Putting the real defaults here
    # would mean nothing is ever asked.


def collect(options, parsed):
    """Return {name: value}, asking for whatever `parsed` did not supply.

    A value given on the command line is used even when it is empty, so
    ``--server ""`` means "leave this flag off" rather than "ask me about it".
    That is the same thing typing "none" at the question does.
    """
    values = {}
    for option in options:
        given = getattr(parsed, option.name, None)

        if option.kind == FLAG:
            values[option.name] = bool(given)
        elif option.kind == YES_NO:
            values[option.name] = (
                given == "yes"
                if given is not None
                else ask_yes_no(option.question, default=option.default)
            )
        else:
            values[option.name] = (
                given
                if given is not None
                else ask(
                    option.question,
                    option.default,
                    require_value=option.is_required(values),
                )
            )
    return values
