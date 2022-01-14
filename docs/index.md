# Jupyter Cache

Execute and cache multiple Jupyter Notebook-like files via an [API](use/api) and [CLI](use/cli).

🤓 Smart re-execution
: Notebooks will only be re-executed when **code cells** have changed (or code related metadata), not Markdown/Raw cells.

🧩 Pluggable execution modes
: Select the executor for notebooks, including serial and parallel execution

📈 Execution reports
: Timing statistics and exception tracebacks are stored for analysis

📖 [jupytext](https://jupytext.readthedocs.io) integration
: Read and execute notebooks written in multiple formats

## Why use jupyter-cache?

If you have a number of notebooks whose execution outputs you want to ensure are kept up to date, without having to re-execute them every time (particularly for long running code, or text-based formats that do not store the outputs).

The notebooks must have deterministic execution outputs:

- You use the same environment to run them (e.g. the same installed packages)
- They run no non-deterministic code (e.g. random numbers)
- They do not depend on external resources (e.g. files or network connections) that change over time

For example, it is utilised by [jupyter-book](https://jupyterbook.org/content/execute.html#caching-the-notebook-execution), to allow for fast document re-builds.

## Installation

Install `jupyter-cache`, via pip or Conda:

```bash
pip install jupyter-cache
```

```bash
conda install jupyter-cache
```

## Quick-start

```{jcache-clear}
```

Add one or more source notebook files to the "project" (a folder containing a database and a cache of executed notebooks):

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: add
:args: tests/notebooks/basic_unrun.ipynb tests/notebooks/basic_failing.ipynb
:input: y
```

These files are now ready for execution:

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: list
```

Now run the execution:

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: execute
```

Successfully executed files will now be associated with a record in the cache:

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: list
```

The cache record includes execution statistics:

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: info
:args: 1
```

Next time we execute, jupyter-cache will check which files require re-execution:

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: execute
```

The source files themselves will not be modified during/after execution.
You can create a new "final" notebook, with the cached outputs merged into the source notebook with:

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: merge
:args: 1 final_notebook.ipynb
```

You can also add notebooks with custom formats, such as those read by [jupytext](https://jupytext.readthedocs.io):

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: add
:args: --reader jupytext tests/notebooks/basic.md
```

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: list
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
- Store execution artefacts: created during execution
- A transparent and robust cache invalidation: imagine the user updating an external dependency or a Python module, or checking out a different git branch.

## Contents

```{toctree}
:caption: Tutorials
using/cli
using/api
```

```{toctree}
:caption: Development
develop/contributing
```
