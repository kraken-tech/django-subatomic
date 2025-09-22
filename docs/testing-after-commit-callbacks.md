### The Problem

Django's after-commit callbacks don't work properly in tests when using `django.db.transaction.atomic`. This creates a disconnect between test behaviour and production behaviour, potentially hiding bugs.

Consider this function that should print `A`, `B`, `C`, `D` in order:

```python
from functools import partial
from django.db import transaction

# application code
def send_notification():
    with transaction.atomic():
        print("A")
        transaction.on_commit(partial(print, "C"))
        print("B")
    print("D")

# test code
def test_with_atomic():
    send_notification()
```

**In production:** This prints `A B C D` as expected.
**In tests:** This prints `A B D` - the after-commit callback never runs!

### Why this happens

Django's `transaction.atomic` blocks can be nested:

- The outermost block creates a transaction
- Inner blocks create savepoints
- After-commit callbacks only run when the actual transaction commits

In production, the full application stack ensures the outermost `transaction.atomic` creates a transaction. In tests, Django cannot determine if a `transaction.atomic` block represents a transaction or savepoint since tests may call functions directly. To be safe, Django never runs after-commit callbacks when `transaction.atomic` blocks exit in tests.

### The Solution: `django_subatomic.db.transaction`

Use `django_subatomic.db.transaction` instead of `django.db.transaction.atomic`, and `django_subatomic.db.run_after_commit` in your application code:

```python
from functools import partial
from django_subatomic import db

# application code
def send_notification():
    with db.transaction():
        print("A")
        db.run_after_commit(partial(print, "C"))
        print("B")
    print("D")

# test code
def test_with_subatomic():
    send_notification()
```

`django_subatomic.db.transaction` explicitly represents a transaction, so tests can safely run after-commit callbacks when it exits. This provides realistic production behaviour without the downsides of other approaches.

## Alternatives considered

Before developing `django-subatomic`, two alternatives approaches were considered to mitigate the above problem of Django's after-commit callbacks not working properly.

### ⚠️ Using pytest-django `django_capture_on_commit_callbacks` fixture (timing issues)

```python
from pytest_django import DjangoCaptureOnCommitCallbacks

def test_with_capture(django_capture_on_commit_callbacks: DjangoCaptureOnCommitCallbacks):
    with django_capture_on_commit_callbacks():
            send_notification()
```

**Result:** `A B D C`
**Problem:** This [`django_capture_on_commit_callbacks`](https://pytest-django.readthedocs.io/en/latest/helpers.html#django-capture-on-commit-callbacks) fixture captures and runs after-commit callbacks, but executes them after the tested function completes. While the callbacks do run, the execution order differs from production, potentially masking timing-dependent bugs.

### ⚠️ Using transaction test cases (slow)

```python
@pytest.mark.django_db(transaction=True)
def test_with_transaction_testcase():
        send_notification()
```

**Result:** `A B C D`
**Problem:** While the callbacks do run and the order of the results are correct, this can be extremely slow in large scale applications because Django must truncate all tables after each test instead of rolling back a transaction.
