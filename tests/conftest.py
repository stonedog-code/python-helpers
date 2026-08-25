"""Shared fixtures.

Every test here drives the real `input()` through a scripted queue rather than
a terminal. That keeps the tier fast and hermetic, and — more usefully — it
lets a test assert the exact prompt string a person would see, which is the
part of a prompt helper most likely to regress unnoticed.
"""

import builtins

import pytest


@pytest.fixture
def answers(monkeypatch):
    """Feed a scripted list of answers to `input()` and record the prompts.

    Usage:

        prompts = answers(["", "Ada"])
        ...
        assert prompts == ["Your name: ", "Your name: "]

    Running off the end of the script raises rather than blocking or looping
    forever: a helper that keeps re-asking is exactly the bug these tests
    exist to catch, and without this it would hang the suite instead of
    failing it.
    """

    def install(script):
        queue = list(script)
        prompts = []

        def fake_input(prompt=""):
            prompts.append(prompt)
            if not queue:
                raise AssertionError(
                    f"input() asked more times than the script allows; "
                    f"prompts so far: {prompts}"
                )
            answer = queue.pop(0)
            if isinstance(answer, BaseException):
                raise answer
            return answer

        monkeypatch.setattr(builtins, "input", fake_input)
        return prompts

    return install
