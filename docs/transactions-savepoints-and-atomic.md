# Transactions and savepoints

When using Django Subatomic,
it helps to know the difference between transactions and savepoints.

## Transactions

Transactions allow multiple database changes to be made atomically.
Inserts, updates (etc) made within a transaction are grouped together
and "committed" (i.e. made visible outside of the transaction) all at once.
If the transaction fails, no changes are committed.

In SQL terms,
a transaction starts with `BEGIN`
and is committed with `COMMIT`.
A transaction can be ended without committing using `ROLLBACK`.

When using Django Subatomic,
transactions are created with [`transaction`][django_subatomic.db.transaction],
which can be used as both a decorator and a context manager.

!!! Note

    SQL does not support nested transactions,
    so nesting is not supported by `transaction`.
    It acts like [Django's `atomic` with `durable=True`][django-atomic]

    See [_Atomic code_](#atomic-code)
    for code which requires a transaction, but doesn't require partial rollback.

    See [_Savepoints_](#savepoints)
    for recovering from failure and continuing within a transaction.

!!! Warning

    Working inside a transaction may not isolate you from changes made outside the transaction.
    For more info see [Transaction Isolation] in PostgreSQL's docs.

## Savepoints

A savepoint is a mark inside a transaction
that allows all commands after it to be rolled back,
restoring the transaction state to what it was at the time of the savepoint.

Savepoints are generally used
to allow a transaction to recover from failure
(such as a database constraint violation)
so that work can continue within the same transaction.

In SQL terms, a savepoint is created with `SAVEPOINT <name>`.
It is rolled back with `ROLLBACK TO <name>`
and discarded with `RELEASE SAVEPOINT <name>`.

Subatomic creates savepoints using [`savepoint`][django_subatomic.db.savepoint].
This is a context manager,
and cannot be used as a decorator.

!!! Tip

    Declare savepoints beside the logic which handles the roll-back behaviour.
    This makes it clear that the savepoint is required, and prevents needless savepoints.

## Atomic code

Sometimes code needs to make multiple database changes atomically
in a place that should not be responsible for managing a transactions.

Decorate this code with [`@transaction_required`][django_subatomic.db.transaction_required]
to make it raise an exception when someone tries to run it without first opening a transaction.

!!! Tip

    Where possible, use [`transaction_required`][django_subatomic.db.transaction_required] as a decorator.

    This form is preferred because it fails earlier,
    and presents a clearer requirement to programmers.

    You can still use [`transaction_required`][django_subatomic.db.transaction_required] as a context manager though.
    This might be useful in code where you cannot know the required database
    (such as when the database name is passed in as a function parameter).

!!! Warning

    When testing code which uses [`transaction_required`][django_subatomic.db.transaction_required],
    you might see `_MissingRequiredTransaction`
    even though tests are run in a transaction by default.

    While unintuitive, this is deliberate.
    It prevents tests from passing
    when they neglect to create a transaction.

    If you are seeing this error when testing high-level code such as a view
    then you have probably forgotten to open a transaction.

    The trade-off is that lower-level tests will see this error too.
    If you're testing [`transaction_required`][django_subatomic.db.transaction_required] code directly,
    and you're _sure_ that the code shouldn't be responsible for opening a transaction,
    use the [`part_of_a_transaction`][django_subatomic.test.part_of_a_transaction] decorator/context-manager
    to get things working.
    This will not run after-commit hooks.
    If you'd like those to run, create a [transaction](#transactions) instead.

When "create-a-transaction-if-one-doesn't-already-exist" behaviour is required,
the [`transaction_if_not_already`][django_subatomic.db.transaction_if_not_already] function will provide it.
This approach hints that transactional behaviour is not well-defined:
the code will do different things in different contexts,
which makes it hard to know what to expect from it.

[transaction isolation]: https://www.postgresql.org/docs/current/transaction-iso.html
[django-atomic]: https://docs.djangoproject.com/en/stable/topics/db/transactions/#django.db.transaction.atomic
