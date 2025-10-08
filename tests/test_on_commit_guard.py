# tests/test_on_commit_guard.py

from django.test import TestCase, override_settings
from django.db import transaction as dj_tx

from django_subatomic import db
from django_subatomic.db import _PendingTestcaseAfterCommitCallbacks


class TestOnCommitGuardWithTransaction(TestCase):
    def test_raises_on_enter_if_testcase_has_pending_callbacks(self):
        dj_tx.on_commit(lambda: None)
        with self.assertRaises(_PendingTestcaseAfterCommitCallbacks):
            with db.transaction():
                pass

    @override_settings(SUBATOMIC_RAISE_IF_PENDING_TESTCASE_ON_COMMIT_ON_ENTER=False)
    def test_opt_out_keeps_previous_behaviour(self):
        calls = []
        dj_tx.on_commit(lambda: calls.append("ok"))
        with db.transaction():
            self.assertEqual(calls, [])
        self.assertEqual(calls, ["ok"])


class TestOnCommitGuardWithTransactionIfNotAlready(TestCase):
    def test_raises_on_enter_in_transaction_if_not_already(self):
        dj_tx.on_commit(lambda: None)
        with self.assertRaises(_PendingTestcaseAfterCommitCallbacks):
            with db.transaction_if_not_already():
                pass

    @override_settings(SUBATOMIC_RAISE_IF_PENDING_TESTCASE_ON_COMMIT_ON_ENTER=False)
    def test_opt_out_keeps_previous_behaviour_in_transaction_if_not_already(self):
        calls = []
        dj_tx.on_commit(lambda: calls.append("ok"))
        with db.transaction_if_not_already():
            self.assertEqual(calls, [])
        self.assertEqual(calls, ["ok"])
