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
will raise `_UnhandledCallbacks` in tests
if it detects any lingering unhandled after-commit callbacks
when it's called.
Note: because this exception represents a programming error,
it starts with an underscore to discourage anyone from catching it.

This highlights order-of-execution issues in tests
caused by after-commit callbacks having not been run.
This can only happen in tests without after-commit callback simulation
(such as those using Django's `atomic` directly),
because in live systems after commit callbacks are always handled or discarded.

The error can be silenced by setting this to `False`,
in which case, the lingering callbacks will be run by the transaction after it commits.

[override_settings]: https://docs.djangoproject.com/en/stable/topics/testing/tools/#django.test.override_settings
[django-settings]: https://docs.djangoproject.com/en/stable/topics/settings/
