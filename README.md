# jupyter-cache

[![Github-CI][github-ci]][github-link]
[![Coverage Status][codecov-badge]][codecov-link]
[![Documentation Status][rtd-badge]][rtd-link]
[![Code style: black][black-badge]][black-link]
[![PyPI][pypi-badge]][pypi-link]

A defined interface for working with a cache of jupyter notebooks.

## Why use jupyter-cache?

If you have a number of notebooks whose execution outputs you want to ensure are kept up to date, without having to re-execute them every time (particularly for long running code, or text-based formats that do not store the outputs).

The notebooks must have deterministic execution outputs:

- You use the same environment to run them (e.g. the same installed packages)
- They run no non-deterministic code (e.g. random numbers)
- They do not depend on external resources (e.g. files or network connections) that change over time

For example, it is utilised by [jupyter-book](https://jupyterbook.org/content/execute.html#caching-the-notebook-execution), to allow for fast document re-builds.

## Install

```bash
pip install jupyter-cache
```

For development:

```bash
git clone https://github.com/executablebooks/jupyter-cache
cd jupyter-cache
git checkout develop
pip install -e .[cli,code_style,testing]
```

See the documentation for usage.

## Development

Some desired requirements (not yet all implemented):

- Persistent
- Separates out "edits to content" from "edits to code cells". Cell
  rearranges and code cell changes should require a re-execution. Content changes should not.
- Allow parallel access to notebooks (for execution)
- Store execution statistics/reports
- Store external assets: Notebooks being executed often require external assets: importing scripts/data/etc. These are prepared by the users.
- Store execution artefacts: created during execution
- A transparent and robust cache invalidation: imagine the user updating an external dependency or a Python module, or checking out a different git branch.

## Contributing

jupyter-cache follows the [Executable Book Contribution Guide](https://executablebooks.org/en/latest/contributing.html). We'd love your help!

### Code Style

Code style is tested using [flake8](http://flake8.pycqa.org),
with the configuration set in `.flake8`,
and code formatted with [black](https://github.com/ambv/black).

Installing with `jupyter-cache[code_style]` makes the [pre-commit](https://pre-commit.com/)
package available, which will ensure this style is met before commits are submitted, by reformatting the code
and testing for lint errors.
It can be setup by:

```shell
>> cd jupyter-cache
>> pre-commit install
```

Optionally you can run `black` and `flake8` separately:

```shell
>> black .
>> flake8 .
```

Editors like VS Code also have automatic code reformat utilities, which can adhere to this standard.

[github-ci]: https://github.com/executablebooks/jupyter-cache/workflows/continuous-integration/badge.svg?branch=master
[github-link]: https://github.com/executablebooks/jupyter-cache
[codecov-badge]: https://codecov.io/gh/executablebooks/jupyter-cache/branch/master/graph/badge.svg
[codecov-link]: https://codecov.io/gh/executablebooks/jupyter-cache
[rtd-badge]: https://readthedocs.org/projects/jupyter-cache/badge/?version=latest
[rtd-link]: https://jupyter-cache.readthedocs.io/en/latest/?badge=latest
[black-badge]: https://img.shields.io/badge/code%20style-black-000000.svg
[pypi-badge]: https://img.shields.io/pypi/v/jupyter-cache.svg
[pypi-link]: https://pypi.org/project/jupyter-cache
[black-link]: https://github.com/ambv/black
