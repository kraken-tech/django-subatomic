# Django Subatomic's features

## Intentional transaction management

...

## No queries wasted on unused savepoints

...

## Fast, production-like tests

Django tests are usually wrapped in a database transaction
which is rolled back when the test completes.
This means that after-commit callbacks would usually never be run.

To simulate realistic production behaviour,
Subatomic runs after-commit callbacks when we exit the
outermost [`transaction`][django_subatomic.db.transaction]
(or [`transaction_if_not_already`][django_subatomic.db.transaction_if_not_already]) context.
This emulates how the application will behave when deployed
and means that tests reproduce realistic application behaviour
without resorting to other more costly or error-prone testing strategies.

## No more accidental immediate "after-commit" callbacks

Subatomic's [`run_after_commit`][django_subatomic.db.run_after_commit] will ensure that
after-commit callbacks are only registered when a transaction is open.
If no transaction is open, an error will be raised.

This is in contrast to the default behaviour of Django's [`on_commit`][on_commit] function,
where after-commit callbacks outside of transactions are executed immediately.

We choose to disallow immediate execution because it can be misleading and hide bugs.
In particular, it can hide the fact that a transaction is missing or on a different database,
which can make code read as though a callback will be deferred when it won't be.

## Progressive integration support

The larger your project is,
the more likely you are to benefit from
the guardrails offered by Django Subatomic's strict features.
Paradoxically, the larger your project is,
the more difficult it may be to enable them all.

Because integrating Django Subatomic all at once
could be a daunting task for larger projects,
we provide some [settings to ease the integration process](/reference/settings).
They allow you to roll out strict behaviour on a per-test basis
using Django's `override_settings`.

[on_commit]: https://docs.djangoproject.com/en/stable/topics/db/transactions/#django.db.transaction.on_commit
[override_settings]: https://docs.djangoproject.com/en/stable/topics/testing/tools/#django.test.override_settings
[TransactionTestCase]: https://docs.djangoproject.com/en/stable/topics/testing/tools/#transactiontestcase
