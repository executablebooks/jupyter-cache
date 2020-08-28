# CHANGELOG

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
