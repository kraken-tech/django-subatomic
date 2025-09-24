## Django's Atomic

Django's `atomic` ensures database changes are committed together-or-not-at-all.
It creates a savepoint or a transaction depending on two factors:

- The arguments passed to it (`durable` and `savepoint`).
- If a database transaction is already open.

Specifically, the **Behaviours** which `atomic` exhibits are:

| `savepoint=`         | `durable=False` (default) | `durable=True` |
| ---                  | ---                       | ---            |
| **`True` (default)** | **A**. Begin a transaction if needed. Creates a savepoint if already in a transaction. | **B**. Begin a transaction, or throw an error if one is already open. Never creates a savepoint. (The `savepoint` flag is ignored.) |
| **`False`**          | **C**. Begin a transaction if needed. Never creates a savepoint. | **D**. Same as **B**.  |

Uses of `atomic` fall into three broad **Categories**:

1. Create a *transaction* to wrap multiple changes.
2. Create a *savepoint* so we can roll back to in order to continue with a transaction after failure.
3. Changes to be committed *atomically*, but not specific about where the transaction is created, as long as there is one.

## Problems

Django's atomic creates many savepoints that are never used.
There are a couple of main causes:

1. Savepoints are created with decorators (`@atomic`).
2. `atomic` creates savepoints by default.
   The default arguments (*Behaviour* **A**)
   are an [attractive nuisance](https://blog.ganssle.io/articles/2023/01/attractive-nuisances.html)
   because they make us create savepoints when we don't need them.

    > … if you have two ways to accomplish a task
    > and one is a simple way
    > that *looks* like the right thing but is subtly wrong,
    > and the other is correct
    > but more complicated,
    > the majority of people will end up doing the wrong thing.
    >
    > — [**Attractive nuisances in software design**](https://blog.ganssle.io/articles/2023/01/attractive-nuisances.html) - [Paul Ganssle](https://blog.ganssle.io/author/paul-ganssle.html)

3. We have no easy way to indicate the creation of a savepoint
  that doesn't have the potential to create a transaction instead.
  The only tool we have to create a savepoint is *Behaviour* **A**,
  which can create a transaction.

## What Subatomic implements
- `transaction()`.
  Begin a transaction, or throw an error if a transaction is already open.
  Like `atomic(durable=True)`, but with added after-commit callback support in tests.
- `savepoint()`.
  Create a savepoint, or throw an error if we're not already in a transaction.
  This is not in the table of *Behaviours*
  (the closest we have is *Behaviour* **A**, but that can create transactions).
- `transaction_if_not_already()`.
  Begin a transaction if we're not already in one.
  Just like *Behaviour* **C**.
  This has a bit of a clunky name.
  This is deliberate, and reflects that it's a bit of a clunky thing to do.
  To be used with caution because the creation of a transaction is implicit.
  For a stricter alternative, see `transaction_required()` below.
- `transaction_required()`.
  Throw an error if we're not already in a transaction.
  Does not create savepoints *or* transactions.
