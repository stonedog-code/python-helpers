"""Unit tests for python_helpers.test.

Two layers. The direct tests call `arrange()` and check what it raises. The
`pytester` tests run a real inner pytest session and check what gets
*reported*: the outcome, the skip reason, and the file and line the skip is
reported at. Those come from pytest's report machinery, which the direct
tests do not exercise.
"""

import pytest

from python_helpers.test import SKIP_PREFIX, arrange


# ── direct: what arrange() raises ────────────────────────────────────────────

def test_a_clean_block_runs_and_its_names_survive_it():
    with arrange():
        value = 42
    assert value == 42


def test_an_exception_becomes_a_skip_naming_it():
    with pytest.raises(pytest.skip.Exception) as info:
        with arrange():
            raise RuntimeError("boom")
    assert info.value.msg == f"{SKIP_PREFIX}: RuntimeError: boom"


def test_the_original_exception_is_kept_as_the_cause():
    original = ValueError("bad store")
    with pytest.raises(pytest.skip.Exception) as info:
        with arrange():
            raise original
    assert info.value.__cause__ is original


def test_an_empty_message_still_names_the_exception_type():
    """An exception with no message must not leave the reason ending at a colon.

    Raised explicitly: pytest rewrites a bare `assert False` in test modules to
    carry the message "assert False", which would hide the empty case.
    """
    with pytest.raises(pytest.skip.Exception) as info:
        with arrange():
            raise AssertionError()
    assert info.value.msg == f"{SKIP_PREFIX}: AssertionError"


def test_pytest_fail_inside_the_block_becomes_a_skip():
    with pytest.raises(pytest.skip.Exception) as info:
        with arrange():
            pytest.fail("no login button")
    assert info.value.msg == f"{SKIP_PREFIX}: Failed: no login button"


def test_pytest_skip_inside_the_block_keeps_its_own_reason():
    with pytest.raises(pytest.skip.Exception) as info:
        with arrange():
            pytest.skip("not on this platform")
    assert info.value.msg == "not on this platform"


# These catch BaseException and then check the type, rather than using
# `pytest.raises(<expected>)`. If arrange() wrongly converted the exception,
# the resulting Skipped would get past a narrow `raises` and skip this test,
# which hides the regression. Measured by planting that regression.

def test_pytest_xfail_inside_the_block_is_not_turned_into_a_skip():
    """XFailed subclasses Failed, so this is the branch most easily broken."""
    with pytest.raises(BaseException) as info:
        with arrange():
            pytest.xfail("known bug")
    assert type(info.value) is pytest.xfail.Exception
    assert info.value.msg == "known bug"


@pytest.mark.parametrize("stop", [KeyboardInterrupt, SystemExit])
def test_stopping_the_run_is_not_turned_into_a_skip(stop):
    with pytest.raises(BaseException) as info:
        with arrange():
            raise stop()
    assert type(info.value) is stop


# ── pytester: what pytest reports ────────────────────────────────────────────

def test_a_failing_arrange_is_reported_as_a_skip(pytester):
    pytester.makepyfile(
        test_orders="""
        from python_helpers.test import arrange

        def test_search():
            with arrange():
                raise TimeoutError("login page never loaded")
            assert False, "must not be reached"
        """
    )
    result = pytester.runpytest("-rs")
    result.assert_outcomes(skipped=1)
    # Line 4 is the `with` line (makepyfile drops the leading newline). The skip
    # is reported there, in the test's own file, rather than inside the helper.
    result.stdout.fnmatch_lines([
        f"SKIPPED*test_orders.py:4: {SKIP_PREFIX}: "
        "TimeoutError: login page never loaded",
    ])


def test_a_failure_after_arrange_is_still_a_failure(pytester):
    pytester.makepyfile(
        """
        from python_helpers.test import arrange

        def test_search():
            with arrange():
                rows = []
            assert len(rows) > 0, "expected the order in the list"
        """
    )
    result = pytester.runpytest()
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*expected the order in the list*"])
