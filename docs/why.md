# Django's Atomic

Django's `atomic` ensures database changes are committed together-or-not-at-all.
It creates a savepoint or a transaction depending on two factors:

- The arguments passed to it (`durable=` and `savepoint=`).
- If a database transaction is already open.

## Behaviours

Specifically, the **Behaviours** which `atomic` exhibits are:

| `savepoint=`         | `durable=False` (default) | `durable=True` |
| ---                  | ---                       | ---            |
| **`True` (default)** | **A**. Begin a transaction if needed. Creates a savepoint if already in a transaction. | **B**. Begin a transaction, or throw an error if one is already open. Never creates a savepoint. (The `savepoint=` flag is ignored.) |
| **`False`**          | **C**. Begin a transaction if needed. Never creates a savepoint. | Same as **B**.  |

## Outcomes

When people use `atomic`,
they're generally trying to achieve one of three **Outcomes**:

1. to create a *transaction*
   which will commit multiple changes atomically.
2. to create a *savepoint*
   so we can roll back to in order to continue with a transaction after failure.
3. to indicate that changes should be committed atomically,
   without needing to be specific about the scope of the transaction,
   as long as there is one.

## Problems

### Ambiguous code

Ideally, we should be able to look at a line of code and say what it will do.

Because `atomic`'s behaviour depends on whether a transaction is already open,
one must know the full call stack
to know what any particular `atomic` will do.
If it is called in multiple code paths,
developers must know that it will do different database operations
depending on who calls it.

Subatomic avoids this issue
by offering an unambiguous API (`transaction()`, `savepoint()`, etc).

### Transactions without context

Low-level code rarely has the context to know when a transaction should be committed.
For example, it may know that its changes must happen atomically,
but cannot know if it is part of a larger suite of changes
managed by higher-level code
which must also be committed together.

When low-level code uses `atomic`
to indicate that its changes should be atomic (*Outcome* **3**),
this can have one of two effects:

- If the higher-level code has opened a transaction,
  the lower-level code will create a savepoint it does not need.

- If the higher-level code has not opened a transaction,
  the lower-level code will.
  While this will achieve the atomicity _it_ demands,
  it fails to ensure that the larger suite of changes
  is also atomic.

Django offers no APIs to indicate
the creation of a savepoint (*Outcome* **2**)
or the need for atomicity (*Outcome* **3**)
that doesn't have the potential to create a transaction instead.

A function decorated with Subatomic's `@transaction_required`
will raise an error when called outside of a transaction,
rather than run the risk of creating a transaction with the wrong scope.

### Savepoints by default

`atomic` defaults to *Behaviour* **A**
which creates savepoints by default
when there is already an open transaction.

It's common to decorate functions with `atomic`
to indicate that code should be atomic (*Outcome* **3**),
but neglect to pass `savepoint=False`.
This results in more database queries than necessary.

Subatomic's `@transaction_required` decorator
gives developers an unambiguous alternative
that will never open a savepoint.

### Savepoints as decorators

Savepoints are intrinsically linked to error handling.
They are only required when we need
a safe place to continue from after a failure within a transaction.
Ideally then, the logic for catching the failure and continuing a transaction
should be adjacent to the logic which creates the savepoint.

When we use `atomic` as a decorator,
we separate the savepoint creation from the error handling logic.
The decorated function will not be within a `try:...except...:`.

This lack of cohesion
can make it difficult to know
where continuing after rolling back a savepoint is intended to be handled,
or even if it is handled at all.
This is compounded by the fact that
because `atomic`'s API is ambiguous,
it can be hard to know the intended *Outcome*.

To encourage putting rollback logic alongside savepoint creation,
Subatomic's `savepoint` cannot be used as a decorator.

### Tests without after-commit callbacks

To avoid leaking state between tests,
Django's `TestCase` runs each test within a transaction
which gets rolled back at the end of the test.
As a result,
`atomic` blocks encountered during the test
will not create transactions
so no after-commit callbacks will be run.

Even if Django wanted to simulate after-commit callbacks in tests,
it has no way to know which *Outcome* was intended
when it encounters an `atomic` block.
It might be running a high-level test where a transaction is intended
and callbacks should be run,
or a low-level test where an open transaction is assumed
and callbacks should _not_ be run.

Without Subatomic,
developers must either manually run after-commit callbacks in tests,
which is prone to error and omission,
or run the test using `TransactionTestCase`,
which can be very slow.

Subatomic's `transaction()` function
will run after-commit callbacks automatically in tests
so that code behaves the same in tests as it does in production.
