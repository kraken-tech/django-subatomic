# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Django 6.0 has been added to the test matrix.
- In tests, an error will now be raised when opening a transaction if there are pre-existing unhandled after-commit callbacks.
  The pre-existing callbacks would previously run when `transaction` exits.
  This helps catch order-of-execution bugs in tests.
  The error can be silenced by setting the `SUBATOMIC_CATCH_UNHANDLED_AFTER_COMMIT_CALLBACKS_IN_TESTS` setting to `False`
  to facilitate gradual adoption of this stricter rule.
- The `transaction`, `transaction_required` and `transaction_if_not_already` decorators can now be used without parentheses. Fixes #103.

### Fixed

- Ensure cleanup actions in `durable` always happen when the wrapped code raises an unexpected error.

### Removed

- `_contextmanager_without_decorator`, `_NonDecoratorContextManager`, `NotADecorator`.
  These implementation details were not intended to be a part of our public API.

## [0.1.1] - 2025-09-20

### Added

- Verified compatibility with Python3.14.
- Minimal documentation.
  N.B. These docs are incomplete.
  More comprehensive documentation
  covering the usage of this library
  and guidance for migrating to it,
  will be published soon.

## [0.1.0] - 2025-09-17

The first release of django-subatomic.

[Unreleased]: https://github.com/kraken-tech/django-subatomic/commits/HEAD
