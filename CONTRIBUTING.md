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

Install the pre-commit hooks so they run automatically on git commit:

```sh
pre-commit install
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

## Docs

Our documentation lives in the `docs/` directory.
It is written in Markdown, and built with [MkDocs].
We use the [Material for MkDocs] theme.
Every time we merge or make a release,
a GitHub Action runs [Mike],
which commits a new version of the docs to the `gh-pages` branch
so that it is deployed to [GitHub Pages].

To build the docs locally, you will need the "docs" dependency-group installed
(if you have already installed the "dev" group, you can skip this):

```
pip install --group docs
```

Once you have the dependencies installed,
you can serve the docs locally with:

```
mkdocs serve
```


[GitHub Pages]: https://pages.github.com/
[Material for MkDocs]: https://squidfunk.github.io/mkdocs-material/
[Mike]: https://github.com/jimporter/mike
[MkDocs]: https://www.mkdocs.org/
[keepachangelog]: https://keepachangelog.com/
[semver]: https://semver.org/
