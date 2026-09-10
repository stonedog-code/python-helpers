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

## `python_helpers.args` — options from the command line, or from a question

Describe each option once. This builds the `--help` **and** asks for whatever
the command line did not supply, so the two halves cannot drift apart.

```python
from python_helpers.args import Option, YES_NO, FLAG, build_parser, collect

OPTIONS = [
    Option("host", "host to connect to", default="localhost", metavar="HOST"),
    Option("confirm", "ask before writing", kind=YES_NO, default=True),
    Option("dry_run", "print and exit", kind=FLAG),
]

parser = build_parser(OPTIONS, prog="tool.py", description="Do the thing.")
values = collect(OPTIONS, parser.parse_args())
#  ./tool.py --host db1   ->  asks only about `confirm`
#  ./tool.py              ->  asks about both
```

Writing an `add_argument` in one place and an `args.x or ask(...)` in another
means every new option is two edits, and the failure when you make only one of
them is silent: the flag parses fine and is then quietly ignored.

### `Option(name, help, default, kind, prompt, metavar, choices, require_value)`

| | |
|---|---|
| `name` | the Python name (`num_parallel`). The flag is **derived** (`--num-parallel`), so the two cannot disagree |
| `kind` | `TEXT` (default), `YES_NO`, or `FLAG`. An unknown kind raises at definition time |
| `default` | for `TEXT` a string (`None` becomes `""`); for `YES_NO` `True`, `False`, or `None` meaning no default. Anything else raises rather than failing later inside the prompt |
| `prompt` | the question text. Defaults to a readable form of the name |
| `require_value` | a bool, **or a callable** taking the values collected so far. Options are collected in list order, so it sees every earlier answer |

`YES_NO` is spelled `--flag yes|no` rather than as a bare switch because a
switch can only turn something *on* — there would be no way to say "no" on the
command line to an option whose default is yes. `FLAG` is never asked about:
prompting for `--dry-run` every run would be asking a question whose answer is
already "no".

### `collect(options, parsed) -> dict`

A value given on the command line is used even when it is empty, so
`--host ""` means "leave this flag off" rather than "ask me about it" — the
same thing typing `none` at the question does.

## `python_helpers.test` — pytest helpers

### `arrange()` — a failed prerequisite skips the test instead of failing it

```python
from python_helpers.test import arrange

@pytest.mark.e2e
def test_order_is_findable_in_search(login_page, api):
    with arrange():
        dashboard = login_page.login(Role.CUSTOMER, user=_USER)
        order_id = api.create_order(store=_STORE)
        api.add_items(order_id, items=_ITEMS, shipping=_SHIPPING)

    rows = dashboard.go_to_orders().search(status="Pending", store=_STORE_LABEL)

    assert rows.count() > 0, f"Expected order {order_id} in the orders list"
```

```console
SKIPPED [1] test_orders.py:3: Prerequisite action failed: TimeoutError: ...
```

A test that could not reach the thing it checks has learned nothing about
that thing. If a shared prerequisite such as login breaks, reporting it as a
failure in every test that needs it hides the real regressions. So any
exception inside the block becomes a skip. The reason names the exception, and
the skip is reported at the test's own `with` line. Anything after the block
fails as usual.

| raised inside the block | result |
|---|---|
| any `Exception`, including `AssertionError` | skip: `Prerequisite action failed: <Type>: <message>` |
| `pytest.fail(...)` | skip, same reason format |
| `pytest.skip(...)` / `pytest.xfail(...)` | left as is, with the author's own reason |
| `KeyboardInterrupt` / `SystemExit` | left as is |

**A run where everything skips reads as green.** If login breaks, every test
that uses `arrange()` skips. Read the skip count alongside the pass count
(`pytest -rs` lists every reason), and keep at least one test that checks each
prerequisite *outside* an `arrange()` block, so a broken one shows up as a
failure somewhere.

This module imports pytest. Install with the `pytest` extra
(`pip install "python-helpers[pytest]"`), or rely on the pytest your test
environment already has.

## Tests

```bash
uv sync
uv run pytest
```

The suite is unit-only: it drives the real `input()` through a scripted queue,
so it is fast, hermetic, and can assert the exact prompt string a person would
see — the part of a prompt helper most likely to regress unnoticed. The
`arrange()` tests also run an in-process pytest session through `pytester`,
because what they check is how pytest reports the outcome.

**Coverage is 100%, branches included, and the gate enforces it** via
`--cov-fail-under=100` in `pyproject.toml`. That matters more than usual for
this module: it is almost entirely loops and early returns, so line coverage
alone would report green while the retry paths — the whole reason the code
exists — had never run.

## Licence

Apache-2.0. See `LICENSE` and `NOTICE`.
