from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from django import db as django_db
from django.db import transaction as django_transaction
from django.test import override_settings

from django_subatomic import db, test


if TYPE_CHECKING:
    import contextlib
    from collections.abc import Callable
    from typing import Protocol

    import pytest_django
    from _pytest.mark.structures import MarkDecorator

    class DBContextManager(Protocol):
        def __call__(
            self, *, using: str | None = None
        ) -> contextlib.AbstractContextManager[None, None]: ...


DEFAULT = "default"
OTHER = "other"

# By default, assume tests in this module need access to the default database.
pytestmark = [pytest.mark.django_db(databases=[DEFAULT])]


def _parametrize_transaction_testcase(func: Callable[..., None]) -> MarkDecorator:
    """
    Make a test run once as a transaction test case, and once as a normal test case.
    """
    parametrize = pytest.mark.parametrize(
        "_is_transaction_testcase",
        (
            pytest.param(
                True,
                id="no transaction",
                marks=[pytest.mark.django_db(transaction=True)],
            ),
            pytest.param(
                False,
                id="testsuite transaction",
                marks=[],
            ),
        ),
    )

    # Decorating the test with `usefixtures` means the test doesn't need
    # to accept _is_transaction_testcase` as a function parameter.
    usefixtures = pytest.mark.usefixtures("_is_transaction_testcase")

    return parametrize(usefixtures(func))  # type: ignore[no-any-return]


class Counter:
    def __init__(self) -> None:
        self.count = 0

    def increment(self) -> None:
        self.count += 1


class _AnError(Exception):
    pass


class TestTransaction:
    @pytest.mark.django_db(transaction=True)
    def test_fails_when_in_tranaction(self) -> None:
        """
        Nested transactions are not allowed.
        """
        with django_transaction.atomic():
            with pytest.raises(
                RuntimeError,
                match=re.escape(
                    "A durable atomic block cannot be nested within another atomic block."
                ),
            ):
                with db.transaction():
                    ...  # An exception is raised before we enter the body of this block.

    @pytest.mark.django_db(transaction=True)
    def test_creates_transaction(self) -> None:
        """
        A transaction is active within the context manager.
        """
        assert django_transaction.get_autocommit() is True

        with db.transaction():
            assert django_transaction.get_autocommit() is False

        assert django_transaction.get_autocommit() is True

    @pytest.mark.django_db(transaction=True)
    def test_decorator(self) -> None:
        """
        `transaction` can be used as a decorator.
        """
        was_called = False

        @db.transaction()
        def inner() -> None:
            assert django_transaction.get_autocommit() is False
            nonlocal was_called
            was_called = True

        assert django_transaction.get_autocommit() is True
        inner()

        assert was_called is True
        assert django_transaction.get_autocommit() is True

    @pytest.mark.django_db(transaction=True)
    def test_decorator_without_parentheses(self) -> None:
        """
        `transaction` can be used as a decorator without parentheses.
        """
        was_called = False

        @db.transaction
        def inner() -> None:
            assert django_transaction.get_autocommit() is False
            nonlocal was_called
            was_called = True

        assert django_transaction.get_autocommit() is True
        inner()

        assert was_called is True
        assert django_transaction.get_autocommit() is True

    def test_works_in_tests(self) -> None:
        """
        Tests can call `db.transaction` without a fuss.

        Django tests are usually run in a transaction. It's worth testing
        to make sure the workarounds from pytest-django work with our tool.
        """
        with db.transaction():
            assert django_transaction.get_autocommit() is False


class TestOnCommitCallbacksInTests:
    @_parametrize_transaction_testcase
    def test_callbacks_executed_when_leaving_transaction(self) -> None:
        """
        Callbacks are executed when exiting the outermost "transaction" block.
        """
        counter = Counter()

        with db.transaction():
            with db.transaction_if_not_already():
                db.run_after_commit(counter.increment)
                assert counter.count == 0

            assert counter.count == 0

        assert counter.count == 1

    @_parametrize_transaction_testcase
    def test_failures_in_callbacks_prevent_others_running(
        self,
    ) -> None:
        """
        If a callback fails, later callbacks do not run.
        """
        counter = Counter()
        transaction_body_end_reached = False

        def raises() -> None:
            raise _AnError

        with pytest.raises(_AnError):
            with db.transaction():
                db.run_after_commit(raises)
                db.run_after_commit(counter.increment)
                transaction_body_end_reached = True

        assert transaction_body_end_reached is True
        # The increment callback is never run.
        assert counter.count == 0

    @_parametrize_transaction_testcase
    def test_failures_in_robust_callbacks_do_not_prevent_others_running(
        self,
    ) -> None:
        """
        If a robust callback fails, later callbacks still run.
        """
        counter = Counter()
        error_raised = False

        def raises() -> None:
            nonlocal error_raised
            error_raised = True
            raise _AnError

        with db.transaction():
            # We use Django's `on_commit` here because `run_after_commit`
            # does not support the `robust` argument.
            django_transaction.on_commit(raises, robust=True)
            db.run_after_commit(counter.increment)
            assert counter.count == 0

        assert error_raised is True
        assert counter.count == 1

    @pytest.mark.parametrize(
        "transaction_manager",
        (db.transaction, db.transaction_if_not_already),
    )
    def test_unhandled_callbacks_cause_error(
        self, transaction_manager: DBContextManager
    ) -> None:
        """
        If callbacks from a previous atomic context remain, raise an error.
        """
        counter = Counter()

        # Django's `atomic` leaves unhandled after-commit actions on exit.
        with django_transaction.atomic():
            db.run_after_commit(counter.increment)

        # `transaction` will raise when it finds the unhandled callback.
        with pytest.raises(db._UnhandledCallbacks) as exc_info:  # noqa: SLF001
            with transaction_manager():
                ...

        assert counter.count == 0
        assert exc_info.value.callbacks == (counter.increment,)

    @pytest.mark.parametrize(
        "transaction_manager",
        (db.transaction, db.transaction_if_not_already),
    )
    def test_unhandled_callbacks_check_can_be_disabled(
        self, transaction_manager: DBContextManager
    ) -> None:
        """
        We can disable the check for unhandled callbacks.
        """
        counter = Counter()

        # Django's `atomic` leaves unhandled after-commit actions on exit.
        with django_transaction.atomic():
            db.run_after_commit(counter.increment)

        # Run after-commit callbacks when `transaction` exits,
        # even if that means running them later than is realistic.
        with override_settings(
            SUBATOMIC_CATCH_UNHANDLED_AFTER_COMMIT_CALLBACKS_IN_TESTS=False
        ):
            with transaction_manager():
                assert counter.count == 0

        assert counter.count == 1

    @pytest.mark.parametrize(
        "transaction_manager",
        (db.transaction, db.transaction_if_not_already),
    )
    def test_handled_callbacks_are_not_an_error(
        self, transaction_manager: DBContextManager
    ) -> None:
        """
        Already-handled checks do not cause an error.
        """
        counter = Counter()

        # Callbacks are handled by `transaction` and removed from the queue.
        with db.transaction():
            db.run_after_commit(counter.increment)
            assert counter.count == 0
        assert counter.count == 1

        # The callbacks have been handled, so a second `transaction` does not raise.
        with transaction_manager():
            pass

        # The callback was not run a second time.
        assert counter.count == 1

    @pytest.mark.parametrize(
        "transaction_manager",
        (db.transaction, db.transaction_if_not_already),
    )
    def test_callbacks_ignored_by_transaction_if_not_already(
        self, transaction_manager: DBContextManager
    ) -> None:
        """
        `transaction_if_not_already` ignores after-commit callbacks if a transaction already exists.
        """
        counter = Counter()

        with transaction_manager():
            db.run_after_commit(counter.increment)
            with db.transaction_if_not_already():
                assert counter.count == 0
            assert counter.count == 0

        # The callback is run when the outermost transaction exits.
        assert counter.count == 1


class TestTransactionRequired:
    @_parametrize_transaction_testcase
    def test_manager_fails_when_not_in_transaction(self) -> None:
        """
        Raise when not in transaction (using transaction testcase).
        """
        with pytest.raises(db._MissingRequiredTransaction) as exc:  # noqa: SLF001
            with db.transaction_required():
                ...  # An exception is raised before we enter the body of this block.

        assert exc.value.database == DEFAULT

    @_parametrize_transaction_testcase
    def test_decorator_fails_when_not_in_transaction(self) -> None:
        """
        An error is raised when we're not in a transaction.
        """

        @db.transaction_required()
        def inner() -> None: ...

        with pytest.raises(db._MissingRequiredTransaction) as exc:  # noqa: SLF001
            inner()

        assert exc.value.database == DEFAULT

    @_parametrize_transaction_testcase
    def test_decorator_without_parentheses_fails_when_not_in_transaction(self) -> None:
        """
        An error is raised when we're not in a transaction.
        """

        @db.transaction_required
        def inner() -> None: ...

        with pytest.raises(db._MissingRequiredTransaction) as exc:  # noqa: SLF001
            inner()

        assert exc.value.database == DEFAULT

    @_parametrize_transaction_testcase
    def test_no_error_when_in_transaction(self) -> None:
        """
        No error is raised when we're in a transaction.
        """
        code_is_reached = False

        with db.transaction():
            with db.transaction_required():
                code_is_reached = True

        assert code_is_reached is True

    @_parametrize_transaction_testcase
    def test_different_database(self) -> None:
        """
        Transactions on other databases do not fulfill the requirement.
        """
        with db.transaction(using=DEFAULT):
            with pytest.raises(db._MissingRequiredTransaction):  # noqa: SLF001
                with db.transaction_required(using=OTHER):
                    ...  # An exception is raised before we enter the body of this block.


class TestSavepointContextManager:
    def test_fails_when_not_in_transaction(self) -> None:
        """
        An error is raised when trying to create a savepoint outside of a transaction.
        """
        # Note: We didn't create a transaction first.
        with pytest.raises(db._MissingRequiredTransaction) as exc:  # noqa: SLF001
            with db.savepoint():
                ...  # An exception is raised before we enter the body of this block.

        assert exc.value.database == DEFAULT

    def test_not_a_decorator(self) -> None:
        """
        `savepoint` cannot be used as a decorator.
        """
        expected_error = "'_ContextManagerOnly' object is not callable"
        with pytest.raises(TypeError, match=expected_error):

            @db.savepoint()  # type: ignore[operator]
            def inner() -> None: ...

    @test.part_of_a_transaction()
    def test_creates_savepoint(
        self, django_assert_num_queries: pytest_django.DjangoAssertNumQueries
    ) -> None:
        """
        `savepoint` creates an SQL SAVEPOINT when in a transaction.
        """
        with django_assert_num_queries(2) as queries:
            with db.savepoint():
                pass

        create_savepoint, release_savepoint = queries

        assert create_savepoint["sql"].startswith("SAVEPOINT ")
        assert release_savepoint["sql"].startswith("RELEASE SAVEPOINT ")


class TestTransactionIfNotAlready:
    def test_transaction_already_exists(
        self, django_assert_num_queries: pytest_django.DjangoAssertNumQueries
    ) -> None:
        with db.transaction():
            # No queries are made to create a transaction if one already exists.
            # In particular, we don't want to see a savepoint created here.
            with django_assert_num_queries(0):
                with db.transaction_if_not_already():
                    pass

    @pytest.mark.django_db(transaction=True)
    def test_no_existing_transaction(
        self, django_assert_num_queries: pytest_django.DjangoAssertNumQueries
    ) -> None:
        assert django_transaction.get_autocommit() is True

        with db.transaction_if_not_already():
            assert django_transaction.get_autocommit() is False

        assert django_transaction.get_autocommit() is True

    def test_cannot_query_after_exception_in_test_case(self) -> None:
        """
        Check that we do not have a working database connection and may not do queries after
        catching an exception and before rolling back.

        The outer atomic block will be unusable because we have not rolled back after the
        exception.
        """
        with db.transaction():
            with pytest.raises(_AnError):
                with db.transaction_if_not_already():
                    raise _AnError

            with pytest.raises(django_transaction.TransactionManagementError):
                with django_db.connections["default"].cursor() as cursor:
                    cursor.execute("SELECT 1")

    def test_can_query_after_exception_in_test_case(self) -> None:
        """
        Check that we have a working database connection and may do queries after catching an exception.

        The test case transaction will be unusable if we do not have a savepoint to roll back to.
        """
        with pytest.raises(_AnError):
            with db.transaction_if_not_already():
                raise _AnError

        with django_db.connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")

    @pytest.mark.django_db(transaction=True)
    def test_decorator(self) -> None:
        """
        `transaction_if_not_already` can be used as a decorator.
        """
        was_called = False

        @db.transaction_if_not_already()
        def inner() -> None:
            assert django_transaction.get_autocommit() is False
            nonlocal was_called
            was_called = True

        assert django_transaction.get_autocommit() is True
        inner()

        assert was_called is True
        assert django_transaction.get_autocommit() is True

    @pytest.mark.django_db(transaction=True)
    def test_decorator_without_parentheses(self) -> None:
        """
        `transaction_if_not_already` can be used as a decorator without parentheses.
        """
        was_called = False

        @db.transaction_if_not_already
        def inner() -> None:
            assert django_transaction.get_autocommit() is False
            nonlocal was_called
            was_called = True

        assert django_transaction.get_autocommit() is True
        inner()

        assert was_called is True
        assert django_transaction.get_autocommit() is True


@db.durable
def _durable_example() -> bool:
    return True


@db.durable
def _create_unclosed_manual_transaction(db_name: str) -> None:
    django_transaction.set_autocommit(False, using=db_name)


@db.durable
def _create_unclosed_manual_transaction_with_error(db_name: str) -> None:
    django_transaction.set_autocommit(False, using=db_name)
    raise KeyError


class TestDurable:
    @_parametrize_transaction_testcase
    def test_not_in_transaction(self) -> None:
        """
        No error is raised when not in a transaction.
        """
        # No error is raised.
        assert _durable_example() is True

    @pytest.mark.django_db(transaction=True, databases=[DEFAULT, OTHER])
    @pytest.mark.parametrize("db_name", [DEFAULT, OTHER])
    def test_in_manual_transaction_without_testcase_transaction(
        self, db_name: str
    ) -> None:
        """
        An error is raised when in a transaction without a testcase transaction.
        """
        with db.transaction(using=db_name):
            with pytest.raises(db._UnexpectedOpenTransaction) as exc_info:  # noqa: SLF001
                _durable_example()

        assert exc_info.value.open_dbs == frozenset({db_name})

    @pytest.mark.parametrize("db_name", [DEFAULT, OTHER])
    @pytest.mark.django_db(databases=[DEFAULT, OTHER])
    def test_in_explicit_transaction(self, db_name: str) -> None:
        """
        An error is raised when in a transaction in a testcase transaction.
        """
        with db.transaction(using=db_name):
            with pytest.raises(db._UnexpectedOpenTransaction) as exc_info:  # noqa: SLF001
                _durable_example()

        assert exc_info.value.open_dbs == frozenset({db_name})

    @pytest.mark.django_db(transaction=True, databases=[DEFAULT, OTHER])
    @pytest.mark.parametrize("db_name", [DEFAULT, OTHER])
    def test_unclosed_manual_transaction(self, db_name: str) -> None:
        """
        Unclosed manual transactions are rolled back with an error.
        """
        # An error is raised.
        with pytest.raises(db._UnexpectedDanglingTransaction) as exc_info:  # noqa: SLF001
            _create_unclosed_manual_transaction(db_name)

        assert exc_info.value.open_dbs == frozenset({db_name})

        # The transaction has been rolled back.
        assert db.in_transaction(using=db_name) is False

    @pytest.mark.django_db(transaction=True, databases=[DEFAULT, OTHER])
    @pytest.mark.parametrize("db_name", [DEFAULT, OTHER])
    def test_unclosed_manual_transaction_after_error(self, db_name: str) -> None:
        with pytest.raises(db._UnexpectedDanglingTransaction) as exc_info:  # noqa: SLF001
            _create_unclosed_manual_transaction_with_error(db_name)

        assert isinstance(exc_info.value.__context__, KeyError)

        assert exc_info.value.open_dbs == frozenset({db_name})

        # The transaction has been rolled back.
        assert db.in_transaction(using=db_name) is False


class TestRunAfterCommit:
    """
    Tests for `run_after_commit`.
    """

    @_parametrize_transaction_testcase
    def test_outside_transaction_error(self) -> None:
        """
        `run_after_commit` should error when asked to execute a callback outside of a transaction.

        See Note [After-commit callbacks require a transaction]
        """
        counter = Counter()

        with pytest.raises(db._MissingRequiredTransaction) as exc:  # noqa: SLF001
            db.run_after_commit(counter.increment, using=DEFAULT)

        assert exc.value.database == DEFAULT
        assert counter.count == 0

    @_parametrize_transaction_testcase
    def test_transaction_check_can_be_disabled(self) -> None:
        """
        Callbacks run immediately if there is no transaction and `SUBATOMIC_AFTER_COMMIT_NEEDS_TRANSACTION` is False.

        See Note [After-commit callbacks require a transaction]
        """
        counter = Counter()

        with override_settings(SUBATOMIC_AFTER_COMMIT_NEEDS_TRANSACTION=False):
            db.run_after_commit(counter.increment)

        assert counter.count == 1

    @_parametrize_transaction_testcase
    @pytest.mark.parametrize(
        "transaction_manager",
        (
            db.transaction,
            db.transaction_if_not_already,
        ),
    )
    def test_executes_after_commit(self, transaction_manager: DBContextManager) -> None:
        """
        `run_after_commit` should execute the callback when the outermost non-testcase transaction exits.

        This checks that we correctly emulate how after-commit callbacks will be run.
        """
        counter = Counter()

        with transaction_manager():
            db.run_after_commit(counter.increment)

            assert counter.count == 0

        assert counter.count == 1

    @pytest.mark.parametrize(
        "expects_transaction",
        (
            db.savepoint,
            db.transaction_required,
        ),
    )
    @test.part_of_a_transaction()
    def test_does_not_execute_without_transaction_with_allow(
        self, expects_transaction: DBContextManager
    ) -> None:
        """
        `run_after_commit` should not execute the callback when a transaction is not being emulated.

        This checks that we correctly emulate how after-commit callbacks will be run.
        """
        counter = Counter()

        with expects_transaction():
            db.run_after_commit(counter.increment)

            assert counter.count == 0

        assert counter.count == 0

    @_parametrize_transaction_testcase
    def test_not_executed_if_rolled_back(self) -> None:
        """
        `run_after_commit` should not execute the callback when a transaction is rolled back.
        """
        counter = Counter()

        try:
            with db.transaction():
                db.run_after_commit(counter.increment)

                assert counter.count == 0

                raise _AnError  # noqa: TRY301
        except _AnError:
            pass

        assert counter.count == 0


class TestRunAfterCommitCallbacksSettingBehaviour:
    @override_settings(SUBATOMIC_AFTER_COMMIT_NEEDS_TRANSACTION=False)
    def test_does_not_execute_when_in_testcase_transaction_if_callbacks_disabled(
        self,
    ) -> None:
        """
        `run_after_commit` should not ignore testcase transactions when SUBATOMIC_RUN_AFTER_COMMIT_CALLBACKS_IN_TESTS is False.

        We have to disable `SUBATOMIC_AFTER_COMMIT_NEEDS_TRANSACTION`, because
        otherwise an error would be raised when trying to register the callback.
        """
        counter = Counter()

        with override_settings(SUBATOMIC_RUN_AFTER_COMMIT_CALLBACKS_IN_TESTS=False):
            db.run_after_commit(counter.increment)

        assert counter.count == 0

    @pytest.mark.parametrize(
        "transaction_context",
        (
            db.transaction,
            db.transaction_if_not_already,
        ),
    )
    def test_does_not_execute_after_commit_if_decorated(
        self, transaction_context: DBContextManager
    ) -> None:
        """
        `run_after_commit` should not execute the callback when SUBATOMIC_RUN_AFTER_COMMIT_CALLBACKS_IN_TESTS is False.
        """
        counter = Counter()

        with override_settings(SUBATOMIC_RUN_AFTER_COMMIT_CALLBACKS_IN_TESTS=False):
            with transaction_context():
                db.run_after_commit(counter.increment)

                assert counter.count == 0

            assert counter.count == 0


class TestInTransaction:
    """
    Tests of `in_transaction`.
    """

    def test_only_in_testcase_transaction(self) -> None:
        """
        We ignore the testcase transaction.
        """
        assert db.in_transaction() is False

    @pytest.mark.django_db(transaction=True)
    def test_not_in_transaction(self) -> None:
        """
        When no transaction is open, the state is reported as such.
        """
        assert db.in_transaction() is False

    @pytest.mark.django_db(transaction=True, databases=[DEFAULT, OTHER])
    @pytest.mark.parametrize(
        "transaction_manager",
        (
            django_transaction.atomic,
            db.transaction,
            db.transaction_if_not_already,
        ),
    )
    def test_transaction_open_on_other_db(
        self, transaction_manager: DBContextManager
    ) -> None:
        """
        A transaction on one database does not affect the transaction state of another.
        """
        with transaction_manager(using=DEFAULT):
            assert db.in_transaction(using=OTHER) is False

    @_parametrize_transaction_testcase
    @pytest.mark.parametrize(
        "transaction_manager",
        (
            django_transaction.atomic,
            db.transaction,
            db.transaction_if_not_already,
        ),
    )
    def test_in_explicit_transaction(
        self, transaction_manager: DBContextManager
    ) -> None:
        """
        Any atomic block is considered a transaction.
        """
        with transaction_manager(using=DEFAULT):
            assert db.in_transaction(using=DEFAULT) is True

    @pytest.mark.django_db(databases=[])
    def test_database_connection_not_opened(self) -> None:
        """
        We don't open a database connection when checking for transaction state.
        """
        # Make sure the database connections are closed.
        for connection in django_db.connections:
            django_db.connections[connection].close()
            assert django_db.connections[connection].connection is None

        # Determine the transaction state.
        for connection in django_db.connections:
            db.in_transaction(using=connection)

        # We should not have opened a database connection.
        # Ideally, if this were to fail, we should see an error before this like:
        #     "Database connections to 'default' are not allowed in this test."
        # Still, this is closest to what we really care about,
        # and the "not allowed" errors aren't currently reliable.
        # See: https://github.com/pytest-dev/pytest-django/issues/1127
        for connection in django_db.connections:
            assert django_db.connections[connection].connection is None


class TestDBsWithOpenTransaction:
    def test_testcase_transaction_ignored(self) -> None:
        """
        We don't count the testcase transaction as an open transaction.
        """
        dbs = db.dbs_with_open_transactions()

        assert dbs == frozenset()

    @pytest.mark.django_db(databases=[DEFAULT, OTHER])
    def test_transactions_open(self) -> None:
        """
        We can detect open transactions.
        """
        with (
            db.transaction(using=DEFAULT),
            db.transaction(using=OTHER),
        ):
            dbs = db.dbs_with_open_transactions()

        assert dbs == frozenset({DEFAULT, OTHER})

    @pytest.mark.django_db(databases=[])
    def test_database_connection_not_opened(self) -> None:
        """
        We don't open a database connection when checking for open transactions.
        """
        # Make sure the database connections are closed.
        for connection in django_db.connections:
            django_db.connections[connection].close()
            assert django_db.connections[connection].connection is None

        # Check for open transactions.
        db.dbs_with_open_transactions()

        # We should not have opened a database connection.
        # Realistically, if this were to fail, we should see an error before this like:
        #     "Database connections to 'default' are not allowed in this test."
        # Still, this is closest to what we really care about,
        # and the "not allowed" errors aren't currently reliable.
        # See: https://github.com/pytest-dev/pytest-django/issues/1127
        for connection in django_db.connections:
            assert django_db.connections[connection].connection is None
