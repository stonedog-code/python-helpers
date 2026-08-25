"""Unit tests for python_helpers.ask.

The module is 100% covered, branches included, and the gate enforces it
(`--cov-fail-under=100` in pyproject.toml). That matters more than usual here:
a prompt helper is almost entirely loops and early returns, so line coverage
alone would report green while the retry paths — the whole reason the module
exists — had never run.
"""

import pytest

from python_helpers.ask import NONE_WORD, ask, ask_yes_no


# ── ask: the plain path ──────────────────────────────────────────────────────

def test_returns_what_was_typed(answers):
    answers(["Ada"])
    assert ask("Your name") == "Ada"


def test_blank_answer_takes_the_default(answers):
    answers([""])
    assert ask("Port", "8080") == "8080"


def test_whitespace_only_answer_takes_the_default(answers):
    """Someone who taps space then Enter meant Enter."""
    answers(["   "])
    assert ask("Port", "8080") == "8080"


def test_answer_is_stripped(answers):
    answers(["  Ada  "])
    assert ask("Your name") == "Ada"


def test_blank_with_no_default_returns_empty(answers):
    answers([""])
    assert ask("Optional note") == ""


# ── ask: the prompt string a person actually sees ────────────────────────────

def test_default_is_shown_in_brackets(answers):
    prompts = answers([""])
    ask("Port", "8080")
    assert prompts == ["Port [8080]: "]


def test_no_brackets_when_there_is_no_default(answers):
    """An empty `[]` would read as "the default is blank" rather than "there
    is no default", so the suffix is omitted entirely."""
    prompts = answers([""])
    ask("Optional note")
    assert prompts == ["Optional note: "]


# ── ask: the "none" escape ───────────────────────────────────────────────────

def test_none_clears_the_value(answers):
    answers([NONE_WORD])
    assert ask("Server", "pp4435") == ""


@pytest.mark.parametrize("typed", ["none", "NONE", "None", "  nOnE  "])
def test_none_is_case_insensitive_and_stripped(answers, typed):
    answers([typed])
    assert ask("Server", "pp4435") == ""


def test_none_as_the_default_also_clears(answers):
    """Enter on a default of "none" goes through the same clearing path — the
    check happens after the default is substituted, not before."""
    answers([""])
    assert ask("Server", NONE_WORD) == ""


def test_a_word_containing_none_is_not_the_escape(answers):
    answers(["none-of-the-above"])
    assert ask("Server") == "none-of-the-above"


# ── ask: require_value ───────────────────────────────────────────────────────

def test_require_value_accepts_a_real_answer_first_time(answers):
    prompts = answers(["Ada"])
    assert ask("Your name", require_value=True) == "Ada"
    assert len(prompts) == 1


def test_require_value_reasks_after_a_blank(answers, capsys):
    prompts = answers(["", "Ada"])
    assert ask("Your name", require_value=True) == "Ada"
    assert len(prompts) == 2
    assert "A value is required." in capsys.readouterr().out


def test_require_value_reasks_after_none(answers, capsys):
    """A required value is one you may not omit, so the escape must not be a
    back door around it."""
    prompts = answers([NONE_WORD, "Ada"])
    assert ask("Your name", require_value=True) == "Ada"
    assert len(prompts) == 2
    assert "A value is required." in capsys.readouterr().out


def test_require_value_reasks_as_many_times_as_needed(answers):
    prompts = answers(["", "", "", "Ada"])
    assert ask("Your name", require_value=True) == "Ada"
    assert len(prompts) == 4


def test_require_value_is_satisfied_by_a_default(answers):
    """The default is a value; pressing Enter on it is a real answer, so this
    must not loop."""
    prompts = answers([""])
    assert ask("Port", "8080", require_value=True) == "8080"
    assert len(prompts) == 1


def test_blank_is_allowed_when_not_required(answers, capsys):
    answers([""])
    assert ask("Optional note") == ""
    assert "A value is required." not in capsys.readouterr().out


# ── ask: cancelling ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("interrupt", [EOFError(), KeyboardInterrupt()])
def test_ctrl_c_and_ctrl_d_exit_rather_than_defaulting(answers, interrupt):
    """The dangerous failure would be returning the default here: the user hit
    Ctrl-C to stop, and proceeding with a value they did not choose is the
    worst possible reading of that."""
    answers([interrupt])
    with pytest.raises(SystemExit) as exc:
        ask("Port", "8080")
    assert "Cancelled." in str(exc.value)


def test_cancelling_mid_retry_still_exits(answers):
    answers(["", EOFError()])
    with pytest.raises(SystemExit):
        ask("Your name", require_value=True)


# ── ask_yes_no ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("typed", ["y", "Y", "yes", "YES", "yep", " y "])
def test_anything_starting_with_y_is_yes(answers, typed):
    answers([typed])
    assert ask_yes_no("Deploy now?") is True


@pytest.mark.parametrize("typed", ["n", "N", "no", "NO", "nope", " n "])
def test_anything_starting_with_n_is_no(answers, typed):
    answers([typed])
    assert ask_yes_no("Deploy now?") is False


def test_returns_a_real_bool(answers):
    """Callers branch on this, and a truthy string would work by accident
    until someone wrote `is True`."""
    answers(["yes"])
    assert isinstance(ask_yes_no("Deploy now?"), bool)


@pytest.mark.parametrize(
    "default, hint, expected",
    [(True, "yes", True), (False, "no", False)],
)
def test_enter_takes_the_default_and_shows_it(answers, default, hint, expected):
    prompts = answers([""])
    assert ask_yes_no("Deploy now?", default=default) is expected
    assert prompts == [f"Deploy now? (yes/no) [{hint}]: "]


def test_no_default_shows_no_brackets_and_keeps_asking(answers):
    """`default=None` means there is no default, so Enter must not resolve to
    a silent False."""
    prompts = answers(["", "yes"])
    assert ask_yes_no("Deploy now?") is True
    assert prompts == ["Deploy now? (yes/no): "] * 2


def test_a_nonsense_answer_reasks_instead_of_guessing(answers, capsys):
    """Guessing here silently changes what the caller goes on to do."""
    prompts = answers(["maybe", "banana", "yes"])
    assert ask_yes_no("Deploy now?") is True
    assert len(prompts) == 3
    assert capsys.readouterr().out.count("Please answer yes or no.") == 2


def test_a_nonsense_answer_reasks_even_with_a_default(answers):
    """The default applies to Enter, not to an answer that was given and could
    not be understood."""
    prompts = answers(["maybe", ""])
    assert ask_yes_no("Deploy now?", default=True) is True
    assert len(prompts) == 2


def test_cancelling_a_yes_no_exits(answers):
    answers([KeyboardInterrupt()])
    with pytest.raises(SystemExit):
        ask_yes_no("Deploy now?")
