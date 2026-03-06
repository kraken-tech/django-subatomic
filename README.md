# Django Subatomic

Subatomic splits [Django's `atomic`][atomic] into a suite of more specific utilities.
It offers precise control over transaction logic in Django projects and transaction simulation in tests.

## Docs

Documentation can be found at <https://kraken-tech.github.io/django-subatomic/>.

## Requirements

This package supports sensible combinations of:

- Python 3.12, 3.13, 3.14.
- Django 4.2, 5.1, 5.2, 6.0.

[atomic]: https://docs.djangoproject.com/en/stable/topics/db/transactions/#django.db.transaction.atomic
