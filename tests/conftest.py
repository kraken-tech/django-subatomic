import os

import pytest
from pytest_django import fixtures


@pytest.fixture(scope="session")
def django_db_modify_db_settings_tox_suffix() -> None:
    """
    Ensure database names don't clash in parallel tox tests.

    This restores `pytest-django`'s compatibility with `tox --parallel` when
    using `tox` v4, which removed `TOX_PARALLEL_ENV`.

    Bug report: https://github.com/pytest-dev/pytest-django/pull/1112
    Removed env var: https://github.com/tox-dev/tox/issues/1275#issuecomment-1012054037
    Fixture docs: https://pytest-django.readthedocs.io/en/stable/database.html#django-db-modify-db-settings-tox-suffix
    """
    # We have no option but to use private functions here
    # because `pytest-django` has no public API for what we're doing.
    fixtures.skip_if_no_django()  # type: ignore[attr-defined]

    tox_environment = os.getenv("TOX_ENV_NAME")

    # We only measure coverage when running tests with tox,
    # so coverage never sees the path where "if tox_environment" is false.
    if tox_environment:  # pragma: no branch
        fixtures._set_suffix_to_test_databases(suffix=tox_environment)  # noqa: SLF001
