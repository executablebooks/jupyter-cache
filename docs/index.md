# Jupyter Cache

This package provides an [API](use/api) and [CLI](use/cli) for executing and cacheing multiple Jupyter Notebook-like files.

Smart re-execution
: Notebooks will only be re-executed when **code cells** have changed (or code related metadata), not Markdown/Raw cells.

Pluggable execution modes
: Select the executor for notebooks, including serial and parallel execution

Execution reports
: Timing statistics and exception tracebacks are stored for analysis

[jupytext](https://jupytext.readthedocs.io) integration
: Read and execute notebooks written in multiple formats

## Installation

Install `jupyter-cache`, via pip or Conda:

```bash
pip install jupyter-cache[cli]
```

```bash
conda install jupyter-cache
```

## Quick-start

```{jcache-clear}
```

Add one or more source notebook files to the "project":

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: add
:args: tests/notebooks/basic_unrun.ipynb tests/notebooks/basic_failing.ipynb
:input: y
```

These files are now ready for execution:

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: list
```

Now run the execution:

```{jcache-cli} jupyter_cache.cli.commands.cmd_main:jcache
:command: execute
:args: --executor local-serial
```

Successfully executed files will now be associated with a record in the cache:

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: list
```

The cache record includes execution statistics:

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: show
:args: 1
```

Next time we execute, jupyter-cache will check which files require re-execution:

```{jcache-cli} jupyter_cache.cli.commands.cmd_main:jcache
:command: execute
```

The source files themselves will not be modified during/after execution.
You can merge the cached outputs into a source notebook with:

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: merge
:args: 1 _executed_notebook.ipynb
```

## Design considerations

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

## Contents

```{toctree}
using/cli
using/api
develop/contributing
```
