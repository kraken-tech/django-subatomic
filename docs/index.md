# Django Subatomic

Subatomic splits [Django's `atomic`][atomic] into a suite of more specific utilities.
It offers precise control over transaction logic in Django projects
and transaction simulation in tests.

## Installation

```sh
pip install django-subatomic
```

## Quick comparison

Subatomic's utilities don't exactly map one-to-one to Django's transactions API,
but the table below is broadly representative.
See the footnotes for some nuance
and the linked API docs for full details.

Desired outcome | Django | Subatomic
--- | --- | ---
Create transaction | `atomic()`[^atomic] | [`transaction()`][django_subatomic.db.transaction][^transaction]
Create savepoint | `atomic()`[^atomic] | [`savepoint()`][django_subatomic.db.savepoint][^savepoint]
Run in a transaction | `atomic()`[^atomic] | [`transaction_required()`][django_subatomic.db.transaction_required][^transaction_required]
Fail if in a transaction | `assert not connection.in_atomic_block` | [`@durable`][django_subatomic.db.durable][^durable]
Run after transaction completes | `transaction.on_commit()` | [`run_after_commit()`][django_subatomic.db.run_after_commit][^run_after_commit]


## Further reading

- [Subatomic's features](features.md).

- [The difference between transactions and savepoints](transactions-savepoints-and-atomic.md).

- [Problems with Django's `atomic`](why.md).

- [Testing after-commit callbacks](testing-after-commit-callbacks.md).


[^atomic]:
    Django's `atomic` creates a savepoint or a transaction depending on two factors:

    - The arguments passed to it (`durable=` and `savepoint=`).
    - If a database transaction is already open.

    For more info, see [Django's atomic](why.md).

[^transaction]:
    Unlike `atomic`,
    which will create a savepoint if a transaction is already open,
    `transaction` ensures the database is not already in a transaction.

[^savepoint]:
    Unlike `atomic`,
    which may create a transaction,
    `savepoint` ensures the database has an active transaction.

[^transaction_required]:
    This ensures that some code is atomic
    by requiring that a transaction is already open.
    Unlike `atomic`, this never creates a transaction or a savepoint.

[^durable]:
    This ensures that code
    may choose to manage its own transactions
    by requiring that a transaction is not already open.

    Note: This shouldn't be confused with `atomic(durable=True)`;
    this never creates a transaction.

[^run_after_commit]:
    Unlike `transaction.on_commit()`,
    this prevents misleading code
    by raising an error if there is no transaction open.


[atomic]: https://docs.djangoproject.com/en/stable/topics/db/transactions/#django.db.transaction.atomic
