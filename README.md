# Django Subatomic

Precise control over transaction logic in Django.

Splits Django's `atomic` into a suite of more specific utilities.


## Prerequisites

This package supports sensible combinations of:

- Python 3.12, 3.13, 3.14.
- Django 4.2, 5.1, 5.2.


### Installation

```sh
pip install django-subatomic
```

## Usage

N.B. These docs are incomplete.
More comprehensive documentation
covering the usage of this library
and guidance for migrating to it,
will be published soon.

`django-subatomic` provides drop-in replacements for `django.db.transaction.atomic`
that make behaviour more explicit
and allow conditions to be expressed without side-effects.

`django-subatomic` does 3 things:

- make transactional behaviour explicit;
- express conditions without side-effects;
- make tests more realistic.

## Make transactional behaviour explicit

### `django.db.transaction.atomic`

Django's `transaction.atomic`
can do multiple things
in several combinations:

- open a transaction
  - optionally: error if one is already open
- create a savepoint within a transaction
- nothing

Some of those behaviours can be chosen
with the `durable` and `savepoint` arguments.
But, it is not always possible to know what it does
without knowing the context in which it is being called.

`django-subatomic` provides utilities
that can be used in place of `atomic`
that each do a specific job:

- `transaction` opens a new transaction
  - it will error if one is already open;
- `savepoint` will create a savepoint
  - it will error if there is no transaction open.

### `django.db.transaction.on_commit`

Django's `on_commit` also behaves differently
depending on the context in which it is called.
If called in a transaction, it registers a callback
to be executed when the transaction commits.
If called with no transaction,
it executes the callback immediately.

`django-subatomic` provides a utility
to register on-commit callbacks,
which fails if there is no transaction to be committed.
This makes the behaviour more obvious for a reader
and interacts more reliably with testcase transactions
(see "Make tests more realistic" below).

## Express conditions without side-effects

Sometimes, code needs to be "atomic",
i.e. it contains multiple database operations
that must either all be committed, or all be rolled back.
It is not possible to enforce that condition
independently from managing transactions
using Django's `atomic`.
(`atomic(savepoint=False)` will never create a savepoint,
but it might start a new transaction.)

Other times,
code needs to be "durable",
i.e. any changes that have been made inside it
*must* persist (or be rolled back)
once the function returns.
There is no way to express this condition with Django's `atomic`
that doesn't also open a new transaction
(which is often exactly what we don't want!)

`django-subatomic` provides two utilities
that allow these conditions to be expressed
without creating transactions or savepoints:

- `transaction_required` will ensure a transaction has been opened
  without creating a savepoint or opening the transaction itself;
- `durable` will ensure a transaction is not currently open,
  without opening one itself.

## Make tests more realistic

Tests are often wrapped in a transaction.
to speed up database use.
This "testcase transaction"
causes Django's `atomic` to behave completely differently in tests
than it will in regular use.

For example,
if a particular call to `atomic` would usually always open a transaction,
e.g. if it were called in a Django view handler function,
in a test it would create a savepoint!
If it used `savepoint=False` it would do nothing at all!

This causes the tests to differ significantly
from real-world usage,
which can lead to tests that do not test the behaviour they want to.
This is particularly relevant when on-commit callbacks are involved.
In the example above,
on-commit callbacks registered during the transaction
would usually be executed when the transaction ended
in the view function.
But, in a test, the transaction is never committed,
so the callbacks are never executed!
That means the behaviour observed in the test
does not match the behaviour of the code in real life.

The utilities for managing transactions in `django-subatomic`
emulate real-world behaviour for on-commit callbacks,
ensuring the testcase transaction does not supress on-commit callbacks.
That makes tests of code that use those utilities
more realistic
and helps to avoid bugs sneaking through automated tests.
