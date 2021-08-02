# Jupyter Cache

A defined interface for working with a cache of jupyter notebooks.

This packages provides a clear [API](use/api) and [CLI](use/cli) for executing and cacheing multiple Jupyter Notebooks in a project.
Although there are certainly other use cases, the principle use case this was written for is generating books / websites, created from multiple notebooks (and other text documents).
It is desired that notebooks can be *auto-executed* **only** if the notebook had been modified in a way that may alter its code cell outputs.

Some desired requirements (not yet all implemented):

- A clear and robust API
- The cache is persistent on disk
- Notebook comparisons separate out "edits to content" from "edits to code cells".
  Cell rearranges and code cell changes should require a re-execution.
  Text content changes should not.
- Allow parallel access to notebooks (for execution)
- Store execution statistics/reports.
- Store external assets: Notebooks being executed often require external assets: importing scripts/data/etc. These are prepared by the users.
- Store execution artifacts: created during execution
- A transparent and robust cache invalidation: imagine the user updating an external dependency or a Python module, or checking out a different git branch.

## Installation

To install `jupyter-cache`, do the following:

```bash
pip install jupyter-cache[cli]
```

For package development:

```bash
git clone https://github.com/ExecutableBookProject/jupyter-cache
cd jupyter-cache
git checkout develop
pip install -e .[cli,code_style,testing,rtd]
```

Here are the site contents:

```{toctree}
using/cli
using/api
develop/contributing
```
