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
    and the real regressions get lost in that noise. So an `Exception` raised
    inside the block becomes a skip whose reason names it:

        SKIPPED test_orders.py:14: Prerequisite action failed: TimeoutError: ...

    Anything that fails after the block is an ordinary failure.

    Only `Exception` is converted. pytest's own outcomes — `pytest.fail()`,
    `pytest.skip()`, `pytest.xfail()` — and KeyboardInterrupt/SystemExit are
    not `Exception`s, so they pass through as whatever the caller asked for.

    Keep only setup in the block. Anything that belongs to the behaviour
    under test would be reported as a skip when it breaks.
    """
    return _Arrange()


class _Arrange:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        # Hide this frame so pytest reports the skip at the test's own `with`
        # line. A @contextmanager cannot do this: contextlib's frame sits in
        # between, so every skip would be reported inside contextlib.py.
        __tracebackhide__ = True
        if isinstance(exc, Exception):
            # The type name matters: a KeyError's message is just "'store'",
            # and a bare assert in a helper module has no message at all.
            name = type(exc).__name__
            reason = f"{name}: {exc}" if str(exc) else name
            pytest.skip(f"{SKIP_PREFIX}: {reason}")
