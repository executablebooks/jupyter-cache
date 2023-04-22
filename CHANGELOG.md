# CHANGELOG

## v0.6.1 2023-04-22

A patch release to fix compatibility with sqlalchemy <1.4.

- FIX: compatibility with SQLAlchemy < 1.4.0 [#105](https://github.com/executablebooks/jupyter-cache/pull/105) @DimitriPapadopoulos

## v0.6.0 2023-04-21

This is a minor release to improve our packaging infrastructure and to support several new versions of dependencies.

### Breaking changes

- ‼️ BREAKING: Drop Python 3.7, add Python 3.11, unpin myst-nb in docs [#96](https://github.com/executablebooks/jupyter-cache/pull/96) ([@choldgraf](https://github.com/choldgraf))

### Updated versions

- Update nbclient requirement from <0.6,>=0.2 to >=0.2,<0.8 [#103](https://github.com/executablebooks/jupyter-cache/pull/103) ([@choldgraf](https://github.com/choldgraf))
- UPDATE: SQLAlchemy 2.0 [#93](https://github.com/executablebooks/jupyter-cache/pull/93) ([@jzluo](https://github.com/jzluo), [@choldgraf](https://github.com/choldgraf))
- 🔧 MAINTAIN: setuptools -> flit [#82](https://github.com/executablebooks/jupyter-cache/pull/82) ([@chrisjsewell](https://github.com/chrisjsewell))

### Contributors to this release

The following people contributed discussions, new ideas, code and documentation contributions, and review.
See [our definition of contributors](https://github-activity.readthedocs.io/en/latest/#how-does-this-tool-define-contributions-in-the-reports).

([GitHub contributors page for this release](https://github.com/executablebooks/jupyter-cache/graphs/contributors?from=2022-01-25&to=2023-04-21&type=c))

@AakashGfude ([activity](https://github.com/search?q=repo%3Aexecutablebooks%2Fjupyter-cache+involves%3AAakashGfude+updated%3A2022-01-25..2023-04-21&type=Issues)) | @choldgraf ([activity](https://github.com/search?q=repo%3Aexecutablebooks%2Fjupyter-cache+involves%3Acholdgraf+updated%3A2022-01-25..2023-04-21&type=Issues)) | @chrisjsewell ([activity](https://github.com/search?q=repo%3Aexecutablebooks%2Fjupyter-cache+involves%3Achrisjsewell+updated%3A2022-01-25..2023-04-21&type=Issues)) | @jstac ([activity](https://github.com/search?q=repo%3Aexecutablebooks%2Fjupyter-cache+involves%3Ajstac+updated%3A2022-01-25..2023-04-21&type=Issues)) | @jzluo ([activity](https://github.com/search?q=repo%3Aexecutablebooks%2Fjupyter-cache+involves%3Ajzluo+updated%3A2022-01-25..2023-04-21&type=Issues)) | @kloczek ([activity](https://github.com/search?q=repo%3Aexecutablebooks%2Fjupyter-cache+involves%3Akloczek+updated%3A2022-01-25..2023-04-21&type=Issues)) | @pre-commit-ci ([activity](https://github.com/search?q=repo%3Aexecutablebooks%2Fjupyter-cache+involves%3Apre-commit-ci+updated%3A2022-01-25..2023-04-21&type=Issues))


## 0.5.0 - 2021-01-25

♻️ REFACTOR: package API/CLI/documentation ([#74](https://github.com/executablebooks/jupyter-cache/pull/74))

This release includes major re-writes to key parts of the package,
to improve the user interface, and add additional functionality for reading and executing notebooks.

Key changes:

1. `stage`/`staging` is now rephrased to `notebook`, plus the addition of `project`, i.e. you add notebooks to a project, then execute them.
2. notebook `read_data` is specified per notebook in the project, allowing for multiple types of file to be read/executed via the CLI (e.g. text-based notebooks via <https://jupytext.readthedocs.io>).
   Before, the read functions were passed directly to the API methods.
3. The executor can be specified with `jbcache execute --executor`, and a parallel notebook executor has been added.
4. Improved execution status indicator in `jbcache project list` and other CLI improvements.
5. Re-write of documentation, including better front page, with quick start guide and better logo.

Dependencies have also been restructured, such that the CLI dependencies (`click`, `tabulate`) are now required,
whereas `nbdime` is now optional (since it is only used for optional notebook diffing).

‼️ Breaking:

The name of the SQL table `nbstage` has been changed to `nbproject`, and `read_data`/`exec_data` fields have been added to the `nbproject`.
This means that reading will fail for caches creted using older versions of the package.
However, the version of `jupyter-cache`, used to create the cache, is now recorded, allowing for the possibility of future automated migrations.

## 0.4.3 - 2021-07-29

⬆️ Allow SQLAlchemy v1.4

## 0.4.2 - 2021-01-17

🐛 FIX: nbfomat v4.5 cell IDs

Version 4.5 notebooks now contain `cell.id` (see [JEP 0062](https://jupyter.org/enhancement-proposals/62-cell-id/cell-id.html#Case-loading-notebook-without-cell-id)).
To deal with this, we always hash the notebooks as v4.4 (with ids removed), since IDs do not affect the execution output.
Merging cached outputs into a notebook now also preserves the input notebook minor version, adding or removing `cell.id` where required.

## 0.4.1 - 2020-08-28

⬆️ UPGRADE: nbclient v0.5

## 0.4.0 - 2020-08-19

- 👌 IMPROVE: Add `allow_errors` execution option to `JupyterExecutorBasic.run_and_cache`

  This can also be set in the notebook metadata: `nb.metadata.execution.allow_errors`
- 👌 IMPROVE: Add `run_in_temp` execution option to `JupyterExecutorBasic.run_and_cache`
- ⬇️ DOWNGRADE: Relax pinning of nbclient

    Since there are reports of issues with version 0.3,
    see: [jupyter/nbclient#58](https://github.com/jupyter/nbclient/issues/58)
- ♻️ REFACTOR: Extract single notebook execution into separate function

    Useful for upstream use.

## 0.3.0 - 2020-08-05

### Improved 👌

- Moved execution functionality from [nbconvert](https://github.com/jupyter/nbconvert) to [nbclient](https://github.com/jupyter/nbclient)
- Fixed UTF8 encoding (for Windows OS), thanks to @phaustin

### Fixed 🐛

- Moved testing from Travis CI to GitHub Actions (and added tests for Windows OS)
