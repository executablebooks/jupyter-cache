(use/cli)=

# Command-Line

Note, you can follow this tutorial by cloning <https://github.com/executablebooks/jupyter-cache>, and running these commands inside it.:
tox
```{jcache-clear}
```

```{jcache-cli} jupyter_cache.cli.commands.cmd_main:jcache
:args: --help
```

The first time the cache is required, it will be lazily created:

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: list
:input: y
```

You can specify the path to the cache, with the `--cache-path` option,
or set the `JUPYTERCACHE` environment variable.

You can also clear it at any time:

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: clear
:input: y
```

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: list
:input: y
```

````{tip}
Execute this in the terminal for auto-completion:

```console
eval "$(_JCACHE_COMPLETE=source jcache)"
```
````

## Adding notebooks to the project

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:args: --help
```

A project consist of a set of notebooks to be executed.

When adding notebooks to the project, they are recorded by their URI (e.g. file path),
i.e. no physical copying takes place until execution time.

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: add
:args: tests/notebooks/basic.ipynb tests/notebooks/basic_failing.ipynb tests/notebooks/basic_unrun.ipynb tests/notebooks/complex_outputs.ipynb tests/notebooks/external_output.ipynb
```

You can list the notebooks in the project, at present none have an existing execution record in the cache:

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: list
```

You can remove a notebook from the project by its URI or ID:

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: remove
:args: 4
```

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: list
```

or clear all notebooks from the project:

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: clear
:input: y
```

## Add a custom reader to read notebook files

By default, notebook files are read using the [nbformat reader](https://nbformat.readthedocs.io/en/latest/api.html#nbformat.read).
However, you can also specify a custom reader, defined by an entry point in the `jcache.readers` group.
Included with jupyter_cache is the [jupytext](https://jupytext.readthedocs.io) reader, for formats like MyST Markdown:

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: add
:args: --reader nbformat tests/notebooks/basic.ipynb tests/notebooks/basic_failing.ipynb
```

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: add
:args: --reader jupytext tests/notebooks/basic.md
```

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: list
```

:::{important}
To use the `jupytext` reader, you must have the `jupytext` package installed.
:::

## Executing the notebooks

Simply call the `execute` command, to execute all notebooks in the project that do not have an existing record in the cache.

Executors are defined by entry points in the `jcache.executors` group.
jupyter-cache includes these executors:

- `local-serial`: execute notebooks with the working directory set to their path, in serial mode (using a single process).
- `local-parallel`: execute notebooks with the working directory set to their path, in parallel mode (using multiple processes).
- `temp-serial`: execute notebooks with a temporary working directory, in serial mode (using a single process).
- `temp-parallel`: execute notebooks with a temporary working directory, in parallel mode (using multiple processes).

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: execute
:args: --executor local-serial
```

Successfully executed notebooks will now have a record in the cache, uniquely identified by the a hash of their code and metadata content:

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: list
:args: --hashkeys
```

These records are then compared to the hashes of notebooks in the project, to find which have up-to-date executions.
Note here both notebooks share the same cached notebook (denoted by `[1]` in the status):

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: list
```

Next time you execute the project, only notebooks which don't match a cached record will be executed:

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: execute
:args: --executor local-serial -v CRITICAL
```

You can also `force` all notebooks to be re-executed:

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: execute
:args: --force
```

If you modify a code cell, the notebook will no longer match a cached notebook or, if you wish to re-execute unchanged notebook(s) (for example if the runtime environment has changed), you can remove their records from the cache (keeping the project record):

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: clear
:input: n
:allow-exception:
```

:::{note}
The number of notebooks in the cache is limited
(current default 1000).
Once this limit is reached, the oldest (last accessed) notebooks begin to be deleted.
change this default with `jcache config cache-limit`
:::

## Analysing executed/excepted notebooks

You can see the elapsed execution time of a notebook via its ID in the cache:

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: info
:args: 1
```

Failed execution tracebacks are also available on the project record:

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: info
:args: --tb tests/notebooks/basic_failing.ipynb
```

```{tip}
Code cells can be tagged with `raises-exception` to let the executor known that a cell *may* raise an exception
(see [this issue on its behaviour](https://github.com/jupyter/nbconvert/issues/730)).
```

## Retrieving executed notebooks

Notebooks added to the project are not modified in any way during or after execution:

You can create a new "final" notebook, with the cached outputs merged into the source notebook with:

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: merge
:args: tests/notebooks/basic.md final_notebook.ipynb
```

## Invalidating cached notebooks

If you want to invalidate a notebook's cached execution,
for example if you have changed the notebook's execution environment,
you can do so by calling the `invalidate` command:

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: invalidate
:args: tests/notebooks/basic.ipynb
```

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: list
```

## Specifying notebooks with assets

When executing in a temporary directory, you may want to specify additional "asset" files that also need to be be copied to this directory for the notebook to run.

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: remove
:args: tests/notebooks/basic.ipynb
```

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: add-with-assets
:args: -nb tests/notebooks/basic.ipynb tests/notebooks/artifact_folder/artifact.txt
```

```{jcache-cli} jupyter_cache.cli.commands.cmd_notebook:cmnd_notebook
:command: info
:args: tests/notebooks/basic.ipynb
```

## Adding notebooks directly to the cache

Pre-executed notebooks can be added to the cache directly, without executing them.

A check will be made that the notebooks look to have been executed correctly,
i.e. the cell execution counts go sequentially up from 1.

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: add
:args: tests/notebooks/complex_outputs.ipynb
:input: y
```

Or to skip the validation:

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: add
:args: --no-validate tests/notebooks/external_output.ipynb
```

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: list
```

:::{tip}
To only show the latest versions of cached notebooks.

```console
$ jcache cache list --latest-only
```

:::

## Diffing notebooks

You can diff any of the cached notebooks with any (external) notebook:

```{warning}
This requires `pip install nbdime`
```

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: diff
:args: 1 tests/notebooks/basic_unrun.ipynb
```
