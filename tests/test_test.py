from __future__ import annotations

import pytest

from django_subatomic import db, test


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

        def _callback_which_should_not_be_called() -> None:
            pytest.fail("Callback should not have been called.")  # pragma: no cover

        with test.part_of_a_transaction():
            db.run_after_commit(_callback_which_should_not_be_called)
