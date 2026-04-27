from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

import attrs
from django.conf import settings
from django.db import transaction


if TYPE_CHECKING:
    from collections.abc import Callable, Generator

__all__ = [
    "part_of_a_transaction",
]


@attrs.frozen
class _UnhandledCallbacks(Exception):
    """
    Raised in tests when unhandled callbacks are found before calling `part_of_a_transaction`.

    This happens when after-commit callbacks are registered
    but not run before trying to open a database transaction.

    The best solution is to ensure the after-commit callbacks are handled first.
    """

    callbacks: tuple[Callable[[], object], ...]


@contextlib.contextmanager
def part_of_a_transaction(using: str | None = None) -> Generator[None]:
    """
    Allow calling "transaction required" code without an explicit transaction.

    This is useful for directly testing code marked with [`transaction_required`][django_subatomic.db.transaction_required]
    without going through other code which is responsible for managing a transaction.

    This works by entering a new "atomic" block, so that the inner-most "atomic"
    isn't the one created by the test-suite.

    In "transaction testcases" this will create a transaction, but if you're writing
    a transaction testcase, you probably want to manage transactions more explicitly
    than by calling this.

    Note that this does not handle after-commit callback simulation. If you need that,
    use [`transaction`][django_subatomic.db.transaction] instead.
    """
    connection = transaction.get_connection(using)
    raise_unhandled_callbacks = getattr(
        settings, "SUBATOMIC_CATCH_UNHANDLED_AFTER_COMMIT_CALLBACKS_IN_TESTS", True
    )

    if raise_unhandled_callbacks:
        callbacks = connection.run_on_commit
        if callbacks:
            raise _UnhandledCallbacks(tuple(callback for _, callback, _ in callbacks))

    with transaction.atomic(using=using, durable=True):
        yield

    # Throw away any callbacks that were registered during the partial transaction,
    # so that they don't pollute later code.
    # We don't need to do this in `try: ... finally:` because Django's roll
    # back logic already clears the callbacks when an exception is raised.
    connection.run_on_commit = []
