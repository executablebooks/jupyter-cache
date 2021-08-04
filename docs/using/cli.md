(use/cli)=

# Command-Line

```{jcache-clear}
```

From the checked-out repository folder:

```{jcache-cli} jupyter_cache.cli.commands.cmd_main:jcache
:args: --help
```

The first time the cache is required, it will be lazily created:

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: list
:input: y
```

````{tip}
Execute this in the terminal for auto-completion:

```console
eval "$(_JCACHE_COMPLETE=source jcache)"
```
````

## Caching Executed Notebooks

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:args: --help
```

Initially there will be no cached notebooks:

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: list
```

You can add notebooks straight into the cache.
When caching, a check will be made that the notebooks look to have been executed
correctly, i.e. the cell execution counts go sequentially up from 1.

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: add
:args: tests/notebooks/basic.ipynb
:input: y
```

Or to skip validation:

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: add
:args: --no-validate tests/notebooks/basic.ipynb tests/notebooks/basic_failing.ipynb tests/notebooks/basic_unrun.ipynb tests/notebooks/complex_outputs.ipynb tests/notebooks/external_output.ipynb
```

Once you've cached some notebooks, you can look at the 'cache records'
for what has been cached.

Each notebook is hashed (code cells and kernel spec only),
which is used to compare against notebooks in the project.
Multiple hashes for the same URI can be added
(the URI is just there for inspection) and the size of the cache is limited
(current default 1000) so that, at this size,
the last accessed records begin to be deleted.
You can remove cached records by their ID.

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: list
```

````{tip}
To only show the latest versions of cached notebooks.

```console
$ jcache cache list --latest-only
```
````

You can also cache notebooks with artefacts
(external outputs of the notebook execution).

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: add-with-artefacts
:args: --no-validate -nb tests/notebooks/basic.ipynb tests/notebooks/artifact_folder/artifact.txt
:input: y
```

Show a full description of a cached notebook by referring to its ID

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: show
:args: 6
```

Note artefact paths must be 'upstream' of the notebook folder:

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: add-with-artefacts
:args: -nb tests/notebooks/basic.ipynb tests/test_db.py
```

To view the contents of an execution artefact:

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: cat-artefact
:args: 6 artifact_folder/artifact.txt
```

You can directly remove a cached notebook by its ID:

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: remove
:args: 4
```

You can also diff any of the cached notebooks with any (external) notebook:

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: diff-nb
:args: 2 tests/notebooks/basic.ipynb
```

## Adding notebooks to the project

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:args: --help
```

A project consist of a set of notebooks to be executed.

Notebooks are recorded as pointers to their URI (e.g. file path),
i.e. no physical copying takes place until execution time.

You can list the notebooks to see which have existing records in the cache (by hash),
and which will require execution:

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: add
:args: tests/notebooks/basic.ipynb tests/notebooks/basic_failing.ipynb tests/notebooks/basic_unrun.ipynb tests/notebooks/complex_outputs.ipynb tests/notebooks/external_output.ipynb
```

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: list
```

You can remove a notebook from the project by its URI or ID:

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: remove
:args: 4
```

You can then run a basic execution of the required notebooks:

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: remove
:args: 6 2
```

```{jcache-cli} jupyter_cache.cli.commands.cmd_main:jcache
:command: execute
```

Successfully executed notebooks will be cached to the cache,
along with any 'artefacts' created by the execution,
that are inside the notebook folder, and data supplied by the executor.

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: list
```

Execution data (such as execution time) will be stored in the cache record:

```{jcache-cli} jupyter_cache.cli.commands.cmd_cache:cmnd_cache
:command: show
:args: 6
```

Failed notebooks will not be cached, but the exception traceback will be added to the notebook's project record:

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: show
:args: 2
```

```{tip}
Code cells can be tagged with `raises-exception` to let the executor known that a cell *may* raise an exception
(see [this issue on its behaviour](https://github.com/jupyter/nbconvert/issues/730)).
```

Once executed you may leave notebooks in the project, for later re-execution, or remove them:

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: clear
:input: y
```

You can also add notebooks to the projects with assets;
external files that are required by the notebook during execution.
As with artefacts, these files must be in the same folder as the notebook,
or a sub-folder.

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: add-with-assets
:args: -nb tests/notebooks/basic.ipynb tests/notebooks/artifact_folder/artifact.txt
```

```{jcache-cli} jupyter_cache.cli.commands.cmd_project:cmnd_project
:command: show
:args: 1
```
