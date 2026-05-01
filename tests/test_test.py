from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest
from django.db import transaction as django_transaction
from django.test import override_settings

from django_subatomic import db, test


if TYPE_CHECKING:
    import contextlib
    from typing import Protocol

    class DBContextManager(Protocol):
        def __call__(
            self, *, using: str | None = None
        ) -> contextlib.AbstractContextManager[None, None]: ...


DEFAULT = "default"
pytestmark = [pytest.mark.django_db(databases=[DEFAULT])]


class TestPartOfATransaction:
    """
    Tests of `part_of_a_transaction`.
    """

    def test_simulates_transaction(self) -> None:
        """
        A transaction appears to be open inside `part_of_a_transaction`.
        """
        assert db.in_transaction() is False

        with test.part_of_a_transaction():
            assert db.in_transaction() is True

        assert db.in_transaction() is False

    def test_callbacks_not_executed_in_normal_test_case(self) -> None:
        """
        Callbacks aren't executed when tests manage the transaction.
        """
        with test.part_of_a_transaction():
            db.run_after_commit(_callback_which_should_not_be_called)

    def test_dangling_callbacks_cause_an_error_on_enter(self) -> None:
        """
        Pre-existing callbacks will be detected and cause an error.
        """
        # Django's `atomic` leaves dangling after-commit callbacks
        # on the test case's transaction.
        with django_transaction.atomic():
            django_transaction.on_commit(_callback_which_should_not_be_called)

        # Ignoring private API here because it's the only way to test this guardrail.
        with pytest.raises(test._UnhandledCallbacks) as exc_info:  # noqa: SLF001
            with test.part_of_a_transaction():
                ...

        assert exc_info.value.callbacks == (_callback_which_should_not_be_called,)

    def test_dangling_callbacks_detection_can_be_disabled(self) -> None:
        """
        Pre-existing callbacks can be ignored with a setting.
        """
        # Django's `atomic` leaves dangling after-commit callbacks
        # on the test case's transaction.
        with django_transaction.atomic():
            django_transaction.on_commit(_callback_which_should_not_be_called)

        # This setting suppresses the guardrail.
        with override_settings(
            SUBATOMIC_CATCH_UNHANDLED_AFTER_COMMIT_CALLBACKS_IN_TESTS=False
        ):
            with test.part_of_a_transaction():
                ...

    def test_remaining_callbacks_cleared_on_exit(self) -> None:
        """
        Any callbacks left at the end of the block are cleared out.
        """
        with test.part_of_a_transaction():
            db.run_after_commit(_callback_which_should_not_be_called)

        # If the callbacks weren't cleared, this would raise an error.
        with db.transaction():
            ...

    def test_remaining_callbacks_cleared_on_error(self) -> None:
        """
        Callbacks left at the end of the block are cleared out when an error is raised.
        """

        class _ArbitraryError(Exception): ...

        with pytest.raises(_ArbitraryError):
            with test.part_of_a_transaction():
                db.run_after_commit(_callback_which_should_not_be_called)
                raise _ArbitraryError

        # If the callbacks weren't cleared, this would raise an error.
        with db.transaction():
            ...

    @pytest.mark.parametrize(
        "transaction_manager",
        (
            db.transaction,
            db.transaction_if_not_already,
            django_transaction.atomic,
            test.part_of_a_transaction,
        ),
    )
    def test_fails_when_nested_inside_an_atomic_block(
        self, transaction_manager: DBContextManager
    ) -> None:
        """
        `part_of_a_transaction` cannot be nested inside another atomic block.
        """
        with transaction_manager():
            with pytest.raises(
                RuntimeError,
                match=re.escape(
                    "A durable atomic block cannot be nested within another atomic block."
                ),
            ):
                with test.part_of_a_transaction():
                    ...


def _callback_which_should_not_be_called() -> None:
    pytest.fail("Callback should not have been called.")  # pragma: no cover
