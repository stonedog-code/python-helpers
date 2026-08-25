"""Terminal prompts with defaults.

    from python_helpers.ask import ask, ask_yes_no

    name = ask("Your name", require_value=True)
    port = ask("Port", "8080")
    if ask_yes_no("Deploy now?", default=False):
        ...
"""

import sys

# Typed at any question to clear the value rather than accept the default.
# Without it a blank answer means "keep the default", so there would be no way
# to say "leave this one out".
NONE_WORD = "none"


def ask(prompt, default="", require_value=False):
    """Ask one question and return the answer as a string.

    Enter accepts `default`, which is shown in brackets when there is one.
    Answering "none" clears the value and returns "".

    With `require_value=True` an empty answer is re-asked instead of returned,
    so the caller never has to handle "" for something it cannot proceed
    without. Note this also rejects "none": a required value is one you are not
    allowed to omit.

    Ctrl-C and Ctrl-D exit rather than returning the default — the user was
    trying to abort, and silently proceeding with a value they did not choose
    is the worst possible reading of that keystroke.
    """
    while True:
        suffix = f" [{default}]" if default else ""
        try:
            answer = input(f"{prompt}{suffix}: ").strip() or default
        except (EOFError, KeyboardInterrupt):
            sys.exit("\nCancelled.")

        if answer.lower() == NONE_WORD:
            answer = ""
        if answer or not require_value:
            return answer
        print("A value is required.")


def ask_yes_no(prompt, default=None):
    """Ask a yes/no question and return a bool.

    `default` is True, False, or None. None means there is no default and the
    question repeats until it is answered — which is why this always asks with
    `require_value=True` underneath.

    Anything starting with y or n counts; anything else re-asks rather than
    being guessed at, because guessing wrong here silently changes what the
    caller goes on to do.
    """
    hint = {True: "yes", False: "no", None: ""}[default]
    while True:
        answer = ask(f"{prompt} (yes/no)", hint, require_value=True).lower()
        if answer.startswith("y"):
            return True
        if answer.startswith("n"):
            return False
        print("Please answer yes or no.")
