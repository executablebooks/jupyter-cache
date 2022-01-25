# Contributing

[![Github-CI][github-ci]][github-link]
[![Coverage Status][codecov-badge]][codecov-link]
[![Documentation Status][rtd-badge]][rtd-link]
[![Code style: black][black-badge]][black-link]
[![PyPI][pypi-badge]][pypi-link]

## Installation

For package development:

```bash
git clone https://github.com/executablebooks/jupyter-cache
cd jupyter-cache
git checkout develop
pip install -e .[cli,code_style,testing,rtd]
```

## Code Style

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

## Testing

For code tests:

```shell
>> cd jupyter-cache
>> pytest
```

For documentation build tests:

```shell
>> cd jupyter-cache/docs
>> make clean
>> make html-strict
```

## Pull Requests

To contribute, make Pull Requests to the `master` branch (this is the default branch). A PR can consist of one or multiple commits. Before you open a PR, make sure to clean up your commit history and create the commits that you think best divide up the total work as outlined above (use `git rebase` and `git commit --amend`). Ensure all commit messages clearly summarise the changes in the header and the problem that this commit is solving in the body.

Merging pull requests: There are three ways of 'merging' pull requests on GitHub:

- Squash and merge: take all commits, squash them into a single one and put it on top of the base branch.
    Choose this for pull requests that address a single issue and are well represented by a single commit.
    Make sure to clean the commit message (title & body)
- Rebase and merge: take all commits and 'recreate' them on top of the base branch. All commits will be recreated with new hashes.
    Choose this for pull requests that require more than a single commit.
    Examples: PRs that contain multiple commits with individually significant changes; PRs that have commits from different authors (squashing commits would remove attribution)
- Merge with merge commit: put all commits as they are on the base branch, with a merge commit on top
    Choose for collaborative PRs with many commits. Here, the merge commit provides actual benefits.

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
