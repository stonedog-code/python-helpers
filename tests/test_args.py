"""Unit tests for python_helpers.args.

The module's whole job is to keep parsing and asking in step, so most of these
assert the *pairing*: an option given on argv is not asked about, and one left
off is. A test that only checked the parser would pass while `collect` ignored
the flag entirely — which is exactly the silent failure this module exists to
prevent.
"""

import pytest

from python_helpers.args import (
    FLAG,
    TEXT,
    YES_NO,
    Option,
    build_parser,
    collect,
)


def parse(options, argv):
    return build_parser(options).parse_args(argv)


# ── Option ───────────────────────────────────────────────────────────────────

def test_flag_is_derived_from_the_name():
    """Deriving rather than declaring is the point: the two cannot disagree."""
    assert Option("num_parallel").flag == "--num-parallel"


def test_flag_of_a_single_word_name():
    assert Option("server").flag == "--server"


def test_question_defaults_to_a_readable_form_of_the_name():
    assert Option("num_parallel").question == "Num parallel"


def test_question_can_be_given_explicitly():
    assert Option("num_parallel", prompt="Parallel workers").question == "Parallel workers"


def test_an_unknown_kind_is_refused_at_definition_time():
    """Better here than as a mystery at parse time, three hundred lines away."""
    with pytest.raises(ValueError, match="unknown kind"):
        Option("server", kind="sometimes")


@pytest.mark.parametrize("kind", [TEXT, YES_NO, FLAG])
def test_every_documented_kind_is_accepted(kind):
    assert Option("thing", kind=kind).kind == kind


# ── Option: defaults mean different things per kind ──────────────────────────

def test_a_text_option_with_no_default_defaults_to_empty_string():
    assert Option("server").default == ""


def test_an_explicit_none_text_default_is_normalised_to_empty_string():
    assert Option("server", default=None).default == ""


@pytest.mark.parametrize("default", [True, False, None])
def test_a_yes_no_default_may_be_true_false_or_none(default):
    """None is meaningful here: no default, so the question repeats."""
    assert Option("record", kind=YES_NO, default=default).default is default


@pytest.mark.parametrize("default", ["yes", "", 1.5])
def test_a_nonsense_yes_no_default_is_refused_at_definition_time(default):
    """Otherwise it reaches ask_yes_no and fails there with a KeyError that
    names neither the option nor the mistake."""
    with pytest.raises(ValueError, match="must be True, False, or None"):
        Option("record", kind=YES_NO, default=default)


# ── Option.is_required ───────────────────────────────────────────────────────

def test_is_required_defaults_to_false():
    assert Option("server").is_required({}) is False


def test_is_required_accepts_a_plain_bool():
    assert Option("server", require_value=True).is_required({}) is True


def test_is_required_accepts_a_callable_over_earlier_answers():
    """The conditional case: mandatory only in some runs."""
    option = Option("user", require_value=lambda values: values["recording"])
    assert option.is_required({"recording": True}) is True
    assert option.is_required({"recording": False}) is False


def test_is_required_coerces_a_callables_result_to_bool():
    assert Option("user", require_value=lambda values: "yes").is_required({}) is True


# ── build_parser ─────────────────────────────────────────────────────────────

def test_a_text_option_parses_its_value():
    parsed = parse([Option("server")], ["--server", "pp4435"])
    assert parsed.server == "pp4435"


def test_an_absent_option_parses_to_none_not_to_its_default():
    """None is the whole mechanism — it is what `collect` reads as "ask me".
    A parser default would mean nothing is ever asked."""
    parsed = parse([Option("server", default="pp4435")], [])
    assert parsed.server is None


def test_a_yes_no_option_parses_yes_and_no():
    option = [Option("record", kind=YES_NO)]
    assert parse(option, ["--record", "yes"]).record == "yes"
    assert parse(option, ["--record", "no"]).record == "no"


def test_a_yes_no_option_rejects_anything_else_at_parse_time(capsys):
    """Caught by argparse rather than reaching the program as a typo."""
    with pytest.raises(SystemExit):
        parse([Option("record", kind=YES_NO)], ["--record", "maybe"])
    assert "invalid choice" in capsys.readouterr().err


def test_a_flag_option_is_a_switch():
    option = [Option("dry_run", kind=FLAG)]
    assert parse(option, ["--dry-run"]).dry_run is True
    assert parse(option, []).dry_run is False


def test_choices_are_enforced_for_a_text_option():
    with pytest.raises(SystemExit):
        parse([Option("env", choices=["dev", "prod"])], ["--env", "banana"])


def test_metavar_defaults_to_the_upper_cased_name():
    help_text = build_parser([Option("server")]).format_help()
    assert "--server SERVER" in help_text


def test_metavar_can_be_given_explicitly():
    help_text = build_parser([Option("server", metavar="HOST")]).format_help()
    assert "--server HOST" in help_text


def test_help_text_reaches_the_help_output():
    help_text = build_parser([Option("server", help="where to deploy")]).format_help()
    assert "where to deploy" in help_text


def test_prog_description_and_epilog_reach_the_help_output():
    help_text = build_parser(
        [Option("server")], prog="deploy.py", description="Deploy it.", epilog="examples:\n  deploy.py"
    ).format_help()
    assert "deploy.py" in help_text
    assert "Deploy it." in help_text
    assert "examples:" in help_text


def test_the_epilogs_line_breaks_survive():
    """The default formatter reflows an examples block into one paragraph."""
    epilog = "examples:\n  first line\n  second line"
    help_text = build_parser([Option("server")], epilog=epilog).format_help()
    assert "  first line\n  second line" in help_text


def test_a_parser_with_no_options_still_builds():
    assert "usage" in build_parser([]).format_help()


# ── collect ──────────────────────────────────────────────────────────────────

def test_a_value_from_argv_is_used_and_not_asked_about(answers):
    prompts = answers([])  # any question at all would blow up the script
    options = [Option("server", default="pp4435")]
    assert collect(options, parse(options, ["--server", "pp9000"])) == {"server": "pp9000"}
    assert prompts == []


def test_a_missing_value_is_asked_for_with_its_default(answers):
    prompts = answers([""])
    options = [Option("server", prompt="Server", default="pp4435")]
    assert collect(options, parse(options, [])) == {"server": "pp4435"}
    assert prompts == ["Server [pp4435]: "]


def test_an_explicit_empty_value_is_kept_rather_than_asked_about(answers):
    """`--server ""` means "leave this flag off", the same as typing "none"."""
    prompts = answers([])
    options = [Option("server", default="pp4435")]
    assert collect(options, parse(options, ["--server", ""])) == {"server": ""}
    assert prompts == []


def test_none_at_the_question_clears_the_value(answers):
    answers(["none"])
    options = [Option("server", default="pp4435")]
    assert collect(options, parse(options, [])) == {"server": ""}


def test_a_required_value_is_reasked(answers):
    prompts = answers(["", "pp9000"])
    options = [Option("server", require_value=True)]
    assert collect(options, parse(options, [])) == {"server": "pp9000"}
    assert len(prompts) == 2


def test_yes_no_from_argv_becomes_a_bool(answers):
    answers([])
    options = [Option("record", kind=YES_NO, default=True)]
    assert collect(options, parse(options, ["--record", "no"])) == {"record": False}
    assert collect(options, parse(options, ["--record", "yes"])) == {"record": True}


def test_yes_no_is_asked_when_absent_and_keeps_its_default(answers):
    prompts = answers([""])
    options = [Option("record", kind=YES_NO, prompt="Record?", default=True)]
    assert collect(options, parse(options, [])) == {"record": True}
    assert prompts == ["Record? (yes/no) [yes]: "]


def test_a_flag_is_never_asked_about(answers):
    """Prompting for --dry-run every run would be asking a question whose
    answer is already no."""
    prompts = answers([])
    options = [Option("dry_run", kind=FLAG)]
    assert collect(options, parse(options, [])) == {"dry_run": False}
    assert collect(options, parse(options, ["--dry-run"])) == {"dry_run": True}
    assert prompts == []


def test_options_are_collected_in_order_so_later_ones_see_earlier_answers(answers):
    """The conditional-requirement case, end to end: `user` is mandatory only
    because `recording` was answered yes a moment earlier."""
    prompts = answers(["yes", "", "Ada"])
    options = [
        Option("recording", kind=YES_NO, prompt="Recording?"),
        Option("user", prompt="User", require_value=lambda values: values["recording"]),
    ]
    assert collect(options, parse(options, [])) == {"recording": True, "user": "Ada"}
    assert len(prompts) == 3  # recording, then user twice


def test_the_same_option_is_optional_when_the_condition_is_false(answers):
    prompts = answers(["no", ""])
    options = [
        Option("recording", kind=YES_NO, prompt="Recording?"),
        Option("user", prompt="User", require_value=lambda values: values["recording"]),
    ]
    assert collect(options, parse(options, [])) == {"recording": False, "user": ""}
    assert len(prompts) == 2


def test_collect_with_no_options_returns_an_empty_dict(answers):
    answers([])
    assert collect([], parse([], [])) == {}
