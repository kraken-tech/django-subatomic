# Django Subatomic

Subatomic splits [Django's `atomic`][atomic] into a suite of more specific utilities.
It gives Django projects precise control over transaction boundaries,
savepoints, durability, and after-commit behaviour in both application code and tests.

## Features

- [x] Fine-grained transaction primitives instead of one overloaded `atomic`
- [x] Explicit separation between transactions, savepoints, and transaction requirements
- [x] Strict `run_after_commit` behaviour that fails fast when no transaction is open
- [x] More realistic test behaviour for after-commit callbacks
- [x] A dedicated `durable` decorator for code that must not run inside a transaction
- [x] Progressive integration settings for adopting strict behaviour in larger existing projects
- [x] Fully typed package with focused, well-documented transaction utilities
- [x] Supports modern Django and Python versions

## Installation

```bash
pip install django-subatomic
```

## Requirements

This package supports sensible combinations of:

- Python 3.12, 3.13, 3.14
- Django 4.2, 5.1, 5.2, 6.0
- SQLite, PostgreSQL, MariaDB

## Documentation

Full documentation is available at <https://kraken-tech.github.io/django-subatomic/>.

## License

[BSD-3-Clause](https://github.com/kraken-tech/django-subatomic/blob/main/LICENSE)

[atomic]: https://docs.djangoproject.com/en/stable/topics/db/transactions/#django.db.transaction.atomic
