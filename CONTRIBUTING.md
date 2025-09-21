# Contributing to Django Subatomic

## Local development

When making changes please remember to update the `CHANGELOG.md`, which follows the guidelines at
[keepachangelog]. Add your changes to the `[Unreleased]` section when you create your PR.

### Installation

Ensure one of the supported versions of Python is installed.

Create and activate a virtual environment with a tool of your choosing.
For example:

```sh
python -m venv .venv
source .venv/bin/activate
```

Once you are in an active virtual environment,
install Python requirements and pre-commit:

```sh
pip install --group dev --editable .
```

### Testing (full requirements matrix)

To test against multiple Python (and package) versions, we need to:

- Ensure that all supported Python versions are installed and available on your system.

- Install [`tox`][tox].
  You can either install it alongside the other requirements
  or install it globally with something like `pipx install tox`.

Then run `tox` with:

```sh
tox
```

Tox will create a separate virtual environment for each combination of Python and package versions
defined in `tox.ini`.

To list the available test environments, run:

```sh
tox list
```

To run the test suite in a specific test environment, use:

```sh
tox -e $ENVNAME

# for example, to run the tests on Python 3.13 with Django 5.2:
tox -e py313-django52
```

To run all test environments in parallel, use:

```sh
tox --parallel
```

[tox]: https://tox.wiki/

### Testing (in current virtual environment)

To run the test suite using the Python version of your virtual environment, run:

```sh
python -m pytest
```

### Static analysis

Run all static analysis tools with:

```sh
pre-commit run --all-files
```

### Dependencies

Python dependencies are declared in `pyproject.toml`.

- _package_ dependencies in the `dependencies` array in the `[project]` section.
- _development_ dependencies in the `[dependency-groups]` section.

[keepachangelog]: https://keepachangelog.com/
[semver]: https://semver.org/
