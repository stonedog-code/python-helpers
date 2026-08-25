"""Small, dependency-free helpers shared across Python projects.

Each module stands alone and imports nothing outside the standard library, so
adding one to a project never drags a dependency tree behind it.

    from python_helpers.ask import ask, ask_yes_no

Nothing is re-exported here on purpose: `from .ask import ask` would make
``python_helpers.ask`` the *function* and shadow the module of the same name,
so the submodule could no longer be imported by its own path.
"""

__version__ = "0.1.0"
