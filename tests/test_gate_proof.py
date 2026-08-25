"""Deliberately failing test, to prove the branch gate actually blocks.

Created once when protection was first applied to main, then deleted. A gate
that has only ever been observed passing has not been tested, it has been run.
"""


def test_this_must_fail():
    assert 1 == 2, "planted failure — this PR must be unmergeable"
