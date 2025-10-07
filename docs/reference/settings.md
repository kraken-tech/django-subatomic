# Settings

Django Subatomic has some custom [Django settings][django-settings]
to help with the process of adopting it in existing projects.

## `SUBATOMIC_AFTER_COMMIT_NEEDS_TRANSACTION`

(default: `True`)

When this setting is `True`,
[`run_after_commit`][django_subatomic.db.run_after_commit] will raise an exception if no transaction is open.

This setting is intended to help projects
transition to this strict behaviour
by getting it working in tests
before enabling it in production.

## `SUBATOMIC_RUN_AFTER_COMMIT_CALLBACKS_IN_TESTS`

(default: `True`)

When this setting is `True`,
after-commit callbacks will be run in tests
when a [`transaction`][django_subatomic.db.transaction]
(or [`transaction_if_not_already`][django_subatomic.db.transaction_if_not_already])
context is exited.

This setting is intended to help projects
progressively enable after-commit callbacks in tests
by using [`override_settings`][override_settings]
on a per-test basis.

[override_settings]: https://docs.djangoproject.com/en/stable/topics/testing/tools/#django.test.override_settings
[django-settings]: https://docs.djangoproject.com/en/stable/topics/settings/
