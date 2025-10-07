from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING

from django.db import transaction


if TYPE_CHECKING:
    from collections.abc import Generator

__all__ = [
    "part_of_a_transaction",
]


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
    with transaction.atomic(using=using):
        yield
