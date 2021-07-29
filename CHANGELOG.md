# CHANGELOG

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
