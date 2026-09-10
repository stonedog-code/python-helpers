"""Helpers for writing pytest tests.

    from python_helpers.test import arrange

    def test_order_is_findable_in_search(login_page, api):
        with arrange():
            dashboard = login_page.login(Role.CUSTOMER, user=_USER)
            order_id = api.create_order(store=_STORE)

        rows = dashboard.go_to_orders().search(status="Pending", store=_STORE)

        assert rows.count() > 0

Unlike the other modules this one imports pytest. It is only ever imported
from test code, where pytest is already present, so the package itself stays
dependency-free.
"""

import pytest

# The skip reason starts with this, so a run's skips can be told apart from
# deliberate `pytest.skip()` calls by grepping `-rs` output for one string.
SKIP_PREFIX = "Prerequisite action failed"


def arrange():
    """Run the arrange step of a test; if it fails, skip the test instead.

    A test that cannot get as far as the thing it checks has not found out
    anything about that thing. Reporting it as a failure puts one broken
    prerequisite — a login, a seed API call — into every test that needs it,
    and the real regressions get lost in that noise. So an exception raised
    inside the block becomes a skip whose reason names the exception:

        SKIPPED test_orders.py:14: Prerequisite action failed: TimeoutError: ...

    Anything that fails after the block is an ordinary failure.

    `pytest.fail()` inside the block is converted too, because page objects
    and API clients often signal "could not do it" that way. `pytest.skip()`
    and `pytest.xfail()` are left alone: the author asked for those outcomes
    and has already given the reason.

    KeyboardInterrupt and SystemExit are not converted either. Someone
    stopping the run does not mean a prerequisite failed.

    Keep only setup in the block. Anything that belongs to the behaviour
    under test would be reported as a skip when it breaks.
    """
    return _Arrange()


class _Arrange:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # Hide this frame so pytest reports the skip at the test's own `with`
        # line. Otherwise every skip would point at this file.
        __tracebackhide__ = True
        # XFailed subclasses Failed, so it is let through before the Failed
        # check below can turn it into a skip.
        if exc is None or isinstance(exc, pytest.xfail.Exception):
            return False
        if isinstance(exc, (Exception, pytest.fail.Exception)):
            raise pytest.skip.Exception(f"{SKIP_PREFIX}: {_describe(exc)}") from exc
        return False


def _describe(exc):
    # A bare `assert` raises an AssertionError with no message. Without the
    # type name the reason would stop at the colon.
    message = str(exc)
    name = type(exc).__name__
    return f"{name}: {message}" if message else name
