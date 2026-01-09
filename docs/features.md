# Features

## Intentional transaction management

Django Subatomic grants precise control over:

- the creation of database [transactions and savepoints](transactions-savepoints-and-atomic.md),
- requirements for [atomicity and durability][acid].

### Unambiguous transactions

Subatomic's [`transaction`][django_subatomic.db.transaction]
unambiguously starts a new database transaction,
unlike Django's [`atomic`][atomic] which sometimes creates a savepoint.

The exact behaviour of `atomic` can be tricky to reason about,
and can lead to [subtle bugs](why.md).
By using Subatomic to explicitly express desired behaviour,
developers are empowered to avoid these bugs.

### Require atomicity separately from transaction management

Subatomic's [`transaction_required`][django_subatomic.db.transaction_required] decorator
allows developers to decouple code which must be run in a transaction
from code which is responsible for the management of that transaction.

Using this instead of an [`atomic`][atomic] decorator also
prevents the [accidental creation of unnecessary savepoints](why.md)
when a transaction is already open.
Subatomic provides the [`savepoint`][django_subatomic.db.savepoint] context manager
for when savepoints _are_ necessary.

### Require durability without creating a transaction

Subatomic provides the [`durable`][django_subatomic.db.durable] decorator
to ensure that a function is called [durably][durable]
without starting a database transaction at the same time.

## No immediate "after-commit" callbacks

Subatomic's [`run_after_commit`][django_subatomic.db.run_after_commit] will ensure that
after-commit callbacks are only registered when a transaction is open.
If no transaction is open, an error will be raised.
This can expose that a transaction is missing or open on a different database,
and prevents code from reading as though a callback will be deferred when it won't be.

This is in contrast to the default behaviour of Django's [`on_commit`][on_commit] function,
where after-commit callbacks outside of transactions are run immediately.

## More realistic tests

Usually,
Django tests are each wrapped in a transaction
which is rolled back when the test completes,
meaning after-commit callbacks are not run.

To simulate realistic production behaviour,
Subatomic runs after-commit callbacks when exiting the
outermost [`transaction`][django_subatomic.db.transaction]
(or [`transaction_if_not_already`][django_subatomic.db.transaction_if_not_already]) context.
This emulates how the application will behave when deployed
and means that tests reproduce realistic application behaviour
without resorting to [other more costly or error-prone testing strategies](testing-after-commit-callbacks.md).

## Progressive integration support

The larger your project is,
the more likely you are to benefit from
the guardrails offered by Django Subatomic's strict features.
Paradoxically, the larger your project is,
the more difficult it may be to enable them all.

Integrating Django Subatomic all at once
could be a daunting task for larger projects,
so we provide some [settings to ease the process](reference/settings.md).
These allow you to progressively roll out strict behaviour
on a per-test or per-feature basis.


[acid]: https://en.wikipedia.org/wiki/ACID
[atomic]: https://docs.djangoproject.com/en/stable/topics/db/transactions/#django.db.transaction.atomic
[durable]: https://en.wikipedia.org/wiki/ACID#Durability
[on_commit]: https://docs.djangoproject.com/en/stable/topics/db/transactions/#django.db.transaction.on_commit
[override_settings]: https://docs.djangoproject.com/en/stable/topics/testing/tools/#django.test.override_settings
[TransactionTestCase]: https://docs.djangoproject.com/en/stable/topics/testing/tools/#transactiontestcase
