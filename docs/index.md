# Jupyter Cache

A defined interface for working with a cache of jupyter notebooks.

```{warning}
This project is in an alpha state. It may evolve rapidly and/or make breaking changes!
Comments, requests, or bugreports are welcome and recommended! Please
[open an issue here](https://github.com/ExecutableBookProject/jupyter-cache/issues)
```

This packages provides a clear [API](use/api) and [CLI](use/cli) for staging, executing and cacheing
Jupyter Notebooks. Although there are certainly other use cases,
the principle use case this was written for is generating books / websites,
created from multiple notebooks (and other text documents),
during which it is desired that notebooks can be *auto-executed* **only**
if the notebook had been modified in a way that may alter its code cell outputs.

Some desired requirements (not yet all implemented):

- A clear and robust API
- The cache is persistent on disk
- Notebook comparisons separate out "edits to content" from "edits to code cells".
  Cell rearranges and code cell changes should require a re-execution.
  Text content changes should not.
- Allow parallel access to notebooks (for execution)
- Store execution statistics/reports.
- Store external assets: Notebooks being executed often require external assets: importing scripts/data/etc. These are prepared by the users.
- Store execution artifacts: created during exeution
- A transparent and robust cache invalidation: imagine the user updating an external dependency or a Python module, or checking out a different git branch.

## Installation

To install `jupytes-cache`, do the following:

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
---
maxdepth: 2
caption: Contents
---
using/cli
using/api
develop/contributing
```
