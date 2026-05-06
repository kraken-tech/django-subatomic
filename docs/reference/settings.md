# Settings

Django Subatomic has some custom [Django settings][django-settings]
to help with the process of adopting it in existing projects.

## `SUBATOMIC_AFTER_COMMIT_NEEDS_TRANSACTION`

(default: `True`)

When this setting is `True`,
[`run_after_commit`][django_subatomic.db.run_after_commit] will raise an exception if no transaction is open.

This setting is intended to help projects
transition to this strict behaviour
by getting it working in tests
before enabling it in production.

## `SUBATOMIC_AFTER_COMMIT_AMBIGUITY_ERROR_IN_TESTS`

(default: `True`)

When this setting is `True`,
[`run_after_commit`][django_subatomic.db.run_after_commit] will ensure that it knows whether or not after-commit callbacks should be simulated in tests.
To avoid silently doing the wrong thing when it is not sure,
[`run_after_commit`][django_subatomic.db.run_after_commit] will raise `subatomic.db._AmbiguousAfterCommitTestBehaviour`.
(This setting starts with an underscore because it is not intended to be caught and handled.)

This can happen in tests when [`run_after_commit`][django_subatomic.db.run_after_commit] is called
inside a Django `atomic` block,
and that `atomic` is directly nested inside the test suite's transaction.
Because the test suite would roll back the transaction,
after-commit callbacks would not normally be run.

Where after-commit callbacks should be run,
this can be fixed by replacing (or wrapping) the `atomic` block with
[`subatomic.db.transaction`][django_subatomic.db.transaction]
(or [`transaction_if_not_already`][django_subatomic.db.transaction_if_not_already] if necessary).

In tests where after-commit callbacks should not be run,
[`part_of_a_transaction`][django_subatomic.test.part_of_a_transaction] should be used instead.

If this setting is `False`,
the after-commit callbacks that this check would catch will not be run.

## `SUBATOMIC_RUN_AFTER_COMMIT_CALLBACKS_IN_TESTS`

(default: `True`)

When this setting is `True`,
after-commit callbacks will be run in tests
when a [`transaction`][django_subatomic.db.transaction]
(or [`transaction_if_not_already`][django_subatomic.db.transaction_if_not_already])
context is exited.

This setting is intended to help projects
progressively enable after-commit callbacks in tests
by using [`override_settings`][override_settings]
on a per-test basis.

## `SUBATOMIC_CATCH_UNHANDLED_AFTER_COMMIT_CALLBACKS_IN_TESTS`

(default: `True`)

[`transaction`][django_subatomic.db.transaction]
and [`transaction_if_not_already`][django_subatomic.db.transaction_if_not_already]
will raise `subatomic.db._UnhandledCallbacks` in tests
if they detect any lingering unhandled after-commit callbacks
when they are called.
[`part_of_a_transaction`][django_subatomic.test.part_of_a_transaction]
will raise `subatomic.test._UnhandledCallbacks` instead.
Note: because these exceptions each represent a programming error,
they start with an underscore to discourage anyone from catching them.

This highlights order-of-execution issues in tests
caused by after-commit callbacks having not been run.
This can only happen in tests without after-commit callback simulation
(such as those using Django's `atomic` directly),
because in live systems after commit callbacks are always handled or discarded.

The error can be silenced by setting this to `False`,
in which case, the lingering callbacks will be run by the transaction after it commits.

[override_settings]: https://docs.djangoproject.com/en/stable/topics/testing/tools/#django.test.override_settings
[django-settings]: https://docs.djangoproject.com/en/stable/topics/settings/
