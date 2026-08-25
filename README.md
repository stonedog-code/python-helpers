# python-helpers

Small, dependency-free helpers shared across Python projects. No runtime
dependencies, by design — a helper that drags a dependency tree behind it is
one people copy-paste instead of importing.

```bash
pip install -e /path/to/python-helpers
```

Or point `PYTHONPATH` at `src/` if the consumer would rather not install
anything.

## `python_helpers.ask` — terminal prompts with defaults

```python
from python_helpers.ask import ask, ask_yes_no

name = ask("Your name", require_value=True)   # re-asks until answered
port = ask("Port", "8080")                    # Enter accepts 8080
host = ask("Host", "localhost")               # "none" clears it to ""
if ask_yes_no("Deploy now?", default=False):
    ...
```

```console
Your name: A value is required.
Your name: Ada
Port [8080]:
Host [localhost]: none
Deploy now? (yes/no) [no]: y
```

### `ask(prompt, default="", require_value=False) -> str`

| | |
|---|---|
| Enter | returns `default` |
| `none` | returns `""` — the only way to say "leave this one out", since blank means "keep the default" |
| `require_value=True` | re-asks on an empty result instead of returning it. Rejects `none` too: a required value is one you may not omit. A `default` satisfies it |
| Ctrl-C / Ctrl-D | exits with `Cancelled.` rather than returning the default |

The default is shown in brackets when there is one, and the brackets are
omitted when there isn't — an empty `[]` reads as "the default is blank"
rather than "there is no default".

### `ask_yes_no(prompt, default=None) -> bool`

Anything starting with `y` or `n` counts, case-insensitively. Anything else
re-asks rather than being guessed at, because guessing wrong here silently
changes what the caller goes on to do.

`default=None` means there is no default and the question repeats until it is
answered — Enter does not resolve to a silent `False`.

## Tests

```bash
uv sync
uv run pytest
```

The suite is unit-only: it drives the real `input()` through a scripted queue,
so it is fast, hermetic, and can assert the exact prompt string a person would
see — the part of a prompt helper most likely to regress unnoticed.

**Coverage is 100%, branches included, and the gate enforces it** via
`--cov-fail-under=100` in `pyproject.toml`. That matters more than usual for
this module: it is almost entirely loops and early returns, so line coverage
alone would report green while the retry paths — the whole reason the code
exists — had never run.

## Licence

Apache-2.0. See `LICENSE` and `NOTICE`.
