# Testing after-commit callbacks

## The Problem

Django's after-commit callbacks don't work properly in tests
when using Django's [`atomic`][atomic].
This creates a disconnect between test behaviour and production behaviour, potentially hiding bugs.

Consider this function that should return `A`, `B`, `C`, `D` in order:

```python
from functools import partial
from django.db import transaction

def build_ABCD():
    my_list = []
    with transaction.atomic():
        my_list.append("A")
        transaction.on_commit(partial(my_list.append, "C"))
        my_list.append("B")
    my_list.append("D")
    return my_list
```

### In production

This returns `["A", "B", "C", "D"]` as expected.

### In tests

```python
from django.test import TestCase

class TestBuildABCD(TestCase):
    def test_build_ABCD():
        built = build_ABCD()
        assert built == ["A", "B", "C", "D"]  # This will fail!
```

This fails because `build_ABCD()` returns `["A", "B", "D"]`,
due to the fact that the after-commit callback never runs!

## Why this happens

Django's [`TestCase`][TestCase] runs each test in a transaction,
which is rolled back at the end of the test to prevent test pollution.
Because the test transaction never commits, Django does not run the after-commit callbacks.

## The Solution: `django_subatomic.db.transaction`

Use Subatomic's [`transaction`][django_subatomic.db.transaction] instead of Django's [`atomic`][atomic] in your application code

```diff
 from functools import partial
+from django_subatomic.db import transaction as subatomic_transaction
 from django.db import transaction as django_transaction

 def build_ABCD():
     my_list = []
-    with transaction.atomic():
+    with subatomic_transaction():
         my_list.append("A")
         django_transaction.on_commit(partial(my_list.append, "C"))
         my_list.append("B")
     my_list.append("D")
     return my_list

```

Subatomic's [`transaction`][django_subatomic.db.transaction] explicitly represents a transaction,
so tests can safely run after-commit callbacks when it exits.
This provides realistic production behaviour without the downsides of other approaches.

## Alternatives considered

Two alternative approaches were available
to mitigate the above problem of Django's after-commit callbacks not working properly,
but with some caveats.

### ⚠️ Using `captureOnCommitCallbacks` (timing issues)

```python

from django.test import TestCase

class TestBuildABCD(TestCase):
    def test_build_ABCD(self):
        with self.captureOnCommitCallbacks(execute=True)
            built = build_ABCD() # This returns `["A", "B", "D", "C"]`
        assert built == ["A", "B", "C", "D"]  # This will fail!
```

[`captureOnCommitCallbacks`][captureOnCommitCallbacks]
captures and runs after-commit callbacks, but executes them after the tested function completes.
While the callbacks do run, the execution order differs from production, potentially masking timing-dependent bugs.

### ⚠️ Using transaction test cases (potentially very slow)

```python
from django.test import TransactionTestCase

class TestBuildABCD(TransactionTestCase)
    def test_build_ABCD():
        built = build_ABCD() # This returns `["A", "B", "C", "D"]`
        assert built == ["A", "B", "C", "D"]
```

While the callbacks do run and the order of the results are correct,
this can be extremely slow in large scale applications,
because Django must truncate all tables after each test instead of rolling back a transaction.

[atomic]: https://docs.djangoproject.com/en/stable/topics/db/transactions/#django.db.transaction.atomic
[captureOnCommitCallbacks]: https://docs.djangoproject.com/en/stable/topics/testing/tools/#django.test.TestCase.captureOnCommitCallbacks
[TestCase]: https://docs.djangoproject.com/en/stable/topics/testing/tools/#django.test.TestCase
