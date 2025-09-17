from __future__ import annotations

import contextlib
import functools
from typing import TYPE_CHECKING

import attrs
from django import db as django_db
from django.conf import settings
from django.db import transaction as django_transaction


if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterator
    from typing import NoReturn


def dbs_with_open_transactions() -> frozenset[str]:
    """
    Get the names of databases with open transactions.
    """
    dbs_with_open_transaction = set()
    # Note: django_db.connections is a special class which implements __iter__,
    # and should not be confused with a list or dict.
    for db_alias in django_db.connections:
        if in_transaction(using=db_alias):
            dbs_with_open_transaction.add(db_alias)

    return frozenset(dbs_with_open_transaction)


def durable[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    """
    Enforce durability with this decorator.

    "Durability" means that the function's work cannot be rolled back after it completes,
    and is not to be confused with "atomicity" (which is about ensuring that the function
    either completes all its work or none of it).

    We enforce this by ensuring that the function is not called within a transaction,
    and that no transaction is left open when the function completes.

    Raises:
        - _UnexpectedOpenTransaction: if a transaction is already open when this is called.

        - _UnexpectedDanglingTransaction: if a transaction remains open after the decorated
          function exits. Before raising this exeption, we roll back and end the transaction.
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        if open_dbs := dbs_with_open_transactions():
            raise _UnexpectedOpenTransaction(open_dbs=open_dbs)

        return_value = func(*args, **kwargs)

        if open_dbs := dbs_with_open_transactions():
            # Clean up first, otherwise we may see errors later that will mask this one.
            # This can only happen if the function manually opens a transaction,
            # so we need to manually roll it back and close it.
            for db_alias in open_dbs:
                django_transaction.rollback(using=db_alias)
                django_transaction.set_autocommit(True, using=db_alias)
            raise _UnexpectedDanglingTransaction(open_dbs=open_dbs)

        return return_value

    return wrapper


@contextlib.contextmanager
def transaction_required(*, using: str | None = None) -> Iterator[None]:
    """
    Make sure that code is always executed in a transaction.

    Can be used as a decorator or a context manager.

    We ignore test-suite transactions when checking for a transaction
    because we don't want to run the risk of allowing code to pass tests
    but fail in production.

    See Note [_MissingRequiredTransaction in tests]

    Raises:
        - _MissingRequiredTransaction: if we are not in a transaction.
    """
    if using is None:
        using = django_db.DEFAULT_DB_ALIAS

    if not in_transaction(using=using):
        raise _MissingRequiredTransaction(database=using)
    yield


@contextlib.contextmanager
def transaction(*, using: str | None = None) -> Iterator[None]:
    """
    Create a database transaction.

    Nested calls are not allowed because SQL does not support nested transactions.
    Consider this like `atomic(durable=True)`, but with added after-commit callback support in tests.

    This wraps Django's 'atomic' function.

    Raises:
        - RuntimeError: if we call this from inside another existing transaction.
    """
    # Note that `savepoint=False` is not required here because
    # the `savepoint` flag is ignored when `durable` is `True`.
    with (
        _execute_on_commit_callbacks_in_tests(using),
        django_transaction.atomic(using=using, durable=True),
    ):
        yield


@contextlib.contextmanager
def transaction_if_not_already(*, using: str | None = None) -> Iterator[None]:
    """
    Create a transaction if one isn't already open.

    Use of this hints at code which lacks control over the state it's called in.

    Suggested altertnatives:

    - In functions which should not control transactions, use `transaction_required`.
      This ensures they are handled by the caller.

    - In functions which can unambiguously control transactions, use `transaction`.
    """
    # If the innermost atomic block is from a test case, we should create a SAVEPOINT here.
    # This allows for a rollback when an exception propagates out of this block, and so
    # better simulates a production transaction behaviour in tests.
    savepoint = _innermost_atomic_block_wraps_testcase(using=using)

    with (
        _execute_on_commit_callbacks_in_tests(using),
        django_transaction.atomic(using=using, savepoint=savepoint),
    ):
        yield


class NotADecorator(Exception):
    """
    Raised when a context manager is mistakenly used as a decorator.
    """


class _NonDecoratorContextManager[T_Co](contextlib._GeneratorContextManager[T_Co]):  # noqa: SLF001
    """
    Hacked version of contextlib._GeneratorContextManager that prevents use as a decorator.

    Use _contextmanager_without_decorator to create instances of this class.

    This is a weird hack, but it beats copying the bulk of the
    contextlib.contextmanager code into our own codebase.
    """

    def __call__(self, func: object) -> NoReturn:
        raise NotADecorator


def _contextmanager_without_decorator[**P, T_Co](
    func: Callable[P, Generator[T_Co, None, None]], /
) -> Callable[P, _NonDecoratorContextManager[T_Co]]:
    """
    Decorate a generator function to make it a context manager.

    This is pretty much the same as `contextlib.contextmanager`,
    but it prevents use as a decorator.
    """

    @functools.wraps(func)
    def helper(*args: P.args, **kwds: P.kwargs) -> _NonDecoratorContextManager[T_Co]:
        return _NonDecoratorContextManager(func, args, kwds)

    return helper


@_contextmanager_without_decorator
def savepoint(*, using: str | None = None) -> Generator[None, None, None]:
    """
    Create a database savepoint.

    Must be called inside an active transaction.

    Tips:
    - You should only create a savepoint if you may roll back to it before
      continuing with your transaction. If your intention is to ensure that
      your code is committed atomically, consider using `transaction_required`
      instead.
    - Savepoint rollback should be handled _where we create the savepoint_.
      That locality is not possible with a decorator, so this function
      deliberately does not work as one.

    Raises:
        - _MissingRequiredTransaction: if we are not in a transaction
          See Note [_MissingRequiredTransaction in tests]
    """
    with (
        transaction_required(using=using),
        django_transaction.atomic(using=using),
    ):
        yield


@contextlib.contextmanager
def _execute_on_commit_callbacks_in_tests(using: str | None = None) -> Iterator[None]:
    """
    Run on-commit callbacks when the outermost non-testcase atomic context exits.

    The part of this function which executes the callbacks
    resembles Django's `run_and_clear_commit_hooks` function.
    It differs because it avoids calling "validate_no_atomic_block`.
    We expect to be in an atomic block opened by the test suite.

    Ref:
    - Django 4.2's `run_and_clear_commit_hooks` function:
        https://github.com/django/django/blob/stable/4.2.x/django/db/backends/base/base.py#L762-L779
    """
    yield
    if (
        # See Note [Running after-commit callbacks in tests]
        getattr(settings, "SUBATOMIC_RUN_AFTER_COMMIT_CALLBACKS_IN_TESTS", True)
        and _innermost_atomic_block_wraps_testcase(using=using)
    ):
        connection = django_transaction.get_connection(using)
        callbacks = connection.run_on_commit
        connection.run_on_commit = []
        for _, callback, robust in callbacks:
            try:
                callback()
            except Exception:
                if not robust:
                    raise


# Note [_MissingRequiredTransaction in tests]
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
#
# Code that uses `db.transaction_required()` (such as `db.savepoint()`) expects
# that a transaction already exists.
#
# Transactions created by the test suite are deliberately ignored.
# This ensures that tests reflect the way that the code will be used in production.
# Specifically, it prevents tests from passing when they call code which forgot to create a transaction.
#
# The downside of this is that when we're directly testing `transaction_required`
# code (without going via the transaction managed in interface code),
# we need to permit the test-suite's transaction.


@attrs.frozen(kw_only=True)
class _MissingRequiredTransaction(Exception):
    """
    Raised by `transaction_required` when we're not in a transaction.

    (Transactions created by the test suite are deliberately ignored.)

    If you're hitting this, it's because of one of two things:

    - You have called code which requires a transaction,
      but no transaction existed at the time of the call.
      Perhaps your code isn't correctly creating a transaction?

    - You're directly testing a function which requires a transaction.
      If you're calling internal code which expects callers to manage the transaction
      wrap your call in `with django_subatomic.test.part_of_a_transaction()`.
      Or, if you also want after-commit callbacks to execute, use `transaction()`.

    See Note [_MissingRequiredTransaction in tests]

    This exception should not be caught, as it indicates a programming error.
    """

    database: str


@attrs.frozen
class _UnexpectedOpenTransaction(Exception):
    """
    Raised when calling a `durable` function with an open transaction.

    (Transactions created by the test suite are deliberately ignored.)

    If you're hitting this, you're calling a function which disallows pre-existing transactions
    while you have a transaction open.

    Perhaps you should use `run_after_commit` to defer calling this durable function?

    This exception should not be caught, as it indicates a programming error.
    """

    open_dbs: frozenset[str]


@attrs.frozen
class _UnexpectedDanglingTransaction(Exception):
    """
    Raised when a `durable` function exits with a transaction open.

    If you're hitting this, a durable function is creating a transaction but not closing it before
    returning.

    This exception should not be caught, as it indicates a programming error.
    """

    open_dbs: frozenset[str]


# Note [After-commit callbacks require a transaction]
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# After-commit callbacks may only be registered when a transaction is open.
# An error will be raised when trying to register an after-commit callback where no transaction is open.
#
# This is in contrast to the default behaviour of Django's `on_commit` function,
# where after-commit callbacks outside of transactions are executed immediately.
#
# We choose to disallow immediate execution because it can be misleading and hide bugs.
# In particular, it can hide the fact that a transaction is missing or on a different database,
# which can make code read as though a callback will be deferred when it won't be.
#
# To help projects migrate to this behaviour, this requirement can be disabled with
# the Django setting `SUBATOMIC_AFTER_COMMIT_NEEDS_TRANSACTION`.


# Note [Running after-commit callbacks in tests]
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Tests are usually wrapped in a database transaction, which is rolled back when the test
# completes. This means that after-commit callbacks would usually never be run.
#
# To avoid that problem, we capture after-commit callbacks and execute them when we exit the
# outermost `transaction` or `transaction_if_not_already` context. This emulates how the application
# will behave when deployed and means that our tests are testing realistic application behaviour.
#
# To help projects migrate to this behaviour, it can be disabled with
# the Django setting `SUBATOMIC_RUN_AFTER_COMMIT_CALLBACKS_IN_TESTS`.


def run_after_commit(
    callback: Callable[[], object],
    *,
    using: str | None = None,
) -> None:
    """
    Register a callback to be called after the current transaction is committed.

    If the current transaction is rolled back, the callback will not be called.
    By default, an error will be raised if there is no transaction open.
    The transaction opened by tests is ignored for this purpose.

    Note that Django's `on_commit` has a `robust` parameter, which allows a callback to fail silently.
    Kraken has a convention to "not allow code to fail silently"
    so this behaviour is not available from this function.
    """
    if using is None:
        using = django_db.DEFAULT_DB_ALIAS

    # See Note [After-commit callbacks require a transaction]
    needs_transaction = getattr(
        settings, "SUBATOMIC_AFTER_COMMIT_NEEDS_TRANSACTION", True
    )
    only_in_testcase_transaction = _innermost_atomic_block_wraps_testcase(using=using)

    # Fail if a transaction is required, but none exists.
    # Ignore test-suite transactions when checking for a transaction.
    # See Note [After-commit callbacks require a transaction]
    if needs_transaction and not in_transaction(using=using):
        raise _MissingRequiredTransaction(database=using)

    if (
        # See Note [Running after-commit callbacks in tests]
        getattr(settings, "SUBATOMIC_RUN_AFTER_COMMIT_CALLBACKS_IN_TESTS", True)
        and only_in_testcase_transaction
    ):
        callback()
    else:
        django_transaction.on_commit(callback, using=using)


def _innermost_atomic_block_wraps_testcase(*, using: str | None = None) -> bool:
    """
    Return True if the current innermost atomic block is wrapping a test case.
    """
    connection = django_transaction.get_connection(using=using)
    # This is based on django.db.transaction.Atomic.__enter__ and uses internal Django fields.
    # It may need updating if django changes how it tracks atomic blocks internally.
    return (
        # check if we are in at least 1 atomic block
        connection.in_atomic_block
        and len(connection.atomic_blocks) > 0
        # and check if the innermost atomic block (last in the stack) is from a test case
        and connection.atomic_blocks[-1]._from_testcase  # noqa: SLF001
    )


def in_transaction(*, using: str | None = None) -> bool:
    """
    Return `True` if the database connection has a transaction active.

    A transaction is active if the connection is no longer in autocommit mode.

    So that code doesn't need to handle how testcase transactions work,
    testcase transactions are not considered a transaction.
    """
    if using is None:
        using = django_db.DEFAULT_DB_ALIAS

    connection = django_db.connections[using]
    if connection.connection is None:
        # If there is no database connection, we can't be in a transaction.
        # We need to check this before checking for an open transaction,
        # because `get_autocommit()` would open a database connection
        # which we might not use and would consume resources unnecessarily.
        return False

    in_transaction = not django_transaction.get_autocommit(using=using)
    if not in_transaction:
        return False

    only_in_testcase_transaction = _innermost_atomic_block_wraps_testcase(using=using)

    # To make this as clear as possible I've spelled out the boolean logic here,
    # and have told ruff to ignore that this could have been simply:
    #
    #     return not only_in_testcase_transaction
    if only_in_testcase_transaction:  # noqa: SIM103
        return False
    else:
        return True
