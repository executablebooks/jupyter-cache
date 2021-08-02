(use/cli)=

# Command-Line

<!-- This section was auto-generated on 2021-08-02 05:12 by: tests/make_cli_readme.py -->

From the checked-out repository folder:

```console
$ jcache --help
Usage: jcache [OPTIONS] COMMAND [ARGS]...

  The command line interface of jupyter-cache.

Options:
  -v, --version       Show the version and exit.
  -p, --cache-path    Print the current cache path and exit.
  -a, --autocomplete  Print the autocompletion command and exit.
  -h, --help          Show this message and exit.

Commands:
  cache    Commands for adding to and inspecting the cache.
  clear    Clear the cache completely.
  config   Commands for configuring the cache.
  execute  Execute all or specific outdated notebooks in the project.
  project  Commands for interacting with a project.
```

````{tip}
Execute this in the terminal for auto-completion:

```console
eval "$(_JCACHE_COMPLETE=source jcache)"
```
````

## Caching Executed Notebooks

```console
$ jcache cache --help
Usage: cache [OPTIONS] COMMAND [ARGS]...

  Commands for adding to and inspecting the cache.

Options:
  --help  Show this message and exit.

Commands:
  add                 Cache notebook(s) that have already been executed.
  add-with-artefacts  Cache a notebook, with possible artefact files.
  cat-artifact        Print the contents of a cached artefact.
  clear               Remove all executed notebooks from the cache.
  diff-nb             Print a diff of a notebook to one stored in the cache.
  list                List cached notebook records in the cache.
  remove              Remove notebooks stored in the cache.
  show                Show details of a cached notebook in the cache.
```

The first time the cache is required, it will be lazily created:

```console
$ jcache cache list
Cache path: ../.jupyter_cache
The cache does not yet exist, do you want to create it? [y/N]: y
No Cached Notebooks

```

You can add notebooks straight into the cache.
When caching, a check will be made that the notebooks look to have been executed
correctly, i.e. the cell execution counts go sequentially up from 1.

```console
$ jcache cache add tests/notebooks/basic.ipynb
Caching: ../tests/notebooks/basic.ipynb
Validity Error: Expected cell 1 to have execution_count 1 not 2
The notebook may not have been executed, continue caching? [y/N]: y
Success!
```

Or to skip validation:

```console
$ jcache cache add --no-validate tests/notebooks/basic.ipynb tests/notebooks/basic_failing.ipynb tests/notebooks/basic_unrun.ipynb tests/notebooks/complex_outputs.ipynb tests/notebooks/external_output.ipynb
Caching: ../tests/notebooks/basic.ipynb
Caching: ../tests/notebooks/basic_failing.ipynb
Caching: ../tests/notebooks/basic_unrun.ipynb
Caching: ../tests/notebooks/complex_outputs.ipynb
Caching: ../tests/notebooks/external_output.ipynb
Success!
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

```console
$ jcache cache list
  ID  Origin URI                             Created           Accessed
----  -------------------------------------  ----------------  ----------------
   5  tests/notebooks/external_output.ipynb  2021-08-02 03:12  2021-08-02 03:12
   4  tests/notebooks/complex_outputs.ipynb  2021-08-02 03:12  2021-08-02 03:12
   3  tests/notebooks/basic_unrun.ipynb      2021-08-02 03:12  2021-08-02 03:12
   2  tests/notebooks/basic_failing.ipynb    2021-08-02 03:12  2021-08-02 03:12
```

````{tip}
To only show the latest versions of cached notebooks.

```console
$ jcache cache list --latest-only
```
````

You can also cache notebooks with artefacts
(external outputs of the notebook execution).

```console
$ jcache cache add-with-artefacts -nb tests/notebooks/basic.ipynb tests/notebooks/artifact_folder/artifact.txt
Caching: ../tests/notebooks/basic.ipynb
Validity Error: Expected cell 1 to have execution_count 1 not 2
The notebook may not have been executed, continue caching? [y/N]: y
Success!
```

Show a full description of a cached notebook by referring to its ID

```console
$ jcache cache show 6
ID: 6
Origin URI: ../tests/notebooks/basic.ipynb
Created: 2021-08-02 03:12
Accessed: 2021-08-02 03:12
Hashkey: 94c17138f782c75df59e989fffa64e3a
Artifacts:
- artifact_folder/artifact.txt
```

Note artefact paths must be 'upstream' of the notebook folder:

```console
$ jcache cache add-with-artefacts -nb tests/notebooks/basic.ipynb tests/test_db.py
Caching: ../tests/notebooks/basic.ipynb
Artifact Error: Path '../tests/test_db.py' is not in folder '../tests/notebooks''
```

To view the contents of an execution artefact:

```console
$ jcache cache cat-artifact 6 artifact_folder/artifact.txt
An artifact

```

You can directly remove a cached notebook by its ID:

```console
$ jcache cache remove 4
Removing Cache ID = 4
Success!
```

You can also diff any of the cached notebooks with any (external) notebook:

```console
$ jcache cache diff-nb 2 tests/notebooks/basic.ipynb
nbdiff
--- cached pk=2
+++ other: ../tests/notebooks/basic.ipynb
## inserted before nb/cells/0:
+  code cell:
+    execution_count: 2
+    source:
+      a=1
+      print(a)
+    outputs:
+      output 0:
+        output_type: stream
+        name: stdout
+        text:
+          1

## deleted nb/cells/0:
-  code cell:
-    source:
-      raise Exception('oopsie!')


Success!
```

## Adding notebooks to the project

```console
$ jcache project --help
Usage: project [OPTIONS] COMMAND [ARGS]...

  Commands for interacting with a project.

Options:
  --help  Show this message and exit.

Commands:
  add              Add notebook(s) to the project.
  add-with-assets  Add notebook(s) to the project, with possible asset files.
  clear            Remove all notebooks from the project.
  list             List notebooks in the project.
  remove           Remove notebook(s) from the project, by ID/URI.
  show             Show details of a notebook.
```

A project consist of a set of notebooks to be executed.

Notebooks are recorded as pointers to their URI (e.g. file path),
i.e. no physical copying takes place until execution time.

You can list the notebooks to see which have existing records in the cache (by hash),
and which will require execution:

```console
$ jcache project add tests/notebooks/basic.ipynb tests/notebooks/basic_failing.ipynb tests/notebooks/basic_unrun.ipynb tests/notebooks/complex_outputs.ipynb tests/notebooks/external_output.ipynb
Adding: ../tests/notebooks/basic.ipynb
Adding: ../tests/notebooks/basic_failing.ipynb
Adding: ../tests/notebooks/basic_unrun.ipynb
Adding: ../tests/notebooks/complex_outputs.ipynb
Adding: ../tests/notebooks/external_output.ipynb
Success!
```

```console
$ jcache project list
  ID  URI                                    Reader    Created             Assets    Cache ID
----  -------------------------------------  --------  ----------------  --------  ----------
   5  tests/notebooks/external_output.ipynb  nbformat  2021-08-02 03:12         0           5
   4  tests/notebooks/complex_outputs.ipynb  nbformat  2021-08-02 03:12         0
   3  tests/notebooks/basic_unrun.ipynb      nbformat  2021-08-02 03:12         0           6
   2  tests/notebooks/basic_failing.ipynb    nbformat  2021-08-02 03:12         0           2
   1  tests/notebooks/basic.ipynb            nbformat  2021-08-02 03:12         0           6
```

You can remove a notebook from the project by its URI or ID:

```console
$ jcache project remove 4
Removing: 4
Success!
```

You can then run a basic execution of the required notebooks:

```console
$ jcache cache remove 6 2
Removing Cache ID = 6
Removing Cache ID = 2
Success!
```

```console
$ jcache execute
Executing: ../tests/notebooks/basic.ipynb
Execution Succeeded: ../tests/notebooks/basic.ipynb
Executing: ../tests/notebooks/basic_failing.ipynb
error: Execution Failed: ../tests/notebooks/basic_failing.ipynb
Executing: ../tests/notebooks/basic_unrun.ipynb
Execution Succeeded: ../tests/notebooks/basic_unrun.ipynb
Executing: ../tests/notebooks/complex_outputs.ipynb
error: Execution Failed: ../tests/notebooks/complex_outputs.ipynb
Finished! Successfully executed notebooks have been cached.
succeeded:
- ../tests/notebooks/basic.ipynb
- ../tests/notebooks/basic_unrun.ipynb
excepted:
- ../tests/notebooks/basic_failing.ipynb
- ../tests/notebooks/complex_outputs.ipynb
errored: []
up-to-date: []

```

Successfully executed notebooks will be cached to the cache,
along with any 'artefacts' created by the execution,
that are inside the notebook folder, and data supplied by the executor.

```console
$ jcache project list
  ID  URI                                    Reader    Created             Assets    Cache ID
----  -------------------------------------  --------  ----------------  --------  ----------
   5  tests/notebooks/external_output.ipynb  nbformat  2021-08-02 03:12         0           5
   4  tests/notebooks/complex_outputs.ipynb  nbformat  2021-08-02 03:12         0
   3  tests/notebooks/basic_unrun.ipynb      nbformat  2021-08-02 03:12         0           6
   2  tests/notebooks/basic_failing.ipynb    nbformat  2021-08-02 03:12         0
   1  tests/notebooks/basic.ipynb            nbformat  2021-08-02 03:12         0           6
```

Execution data (such as execution time) will be stored in the cache record:

```console
$ jcache cache show 6
ID: 6
Origin URI: ../tests/notebooks/basic_unrun.ipynb
Created: 2021-08-02 03:12
Accessed: 2021-08-02 03:12
Hashkey: 94c17138f782c75df59e989fffa64e3a
Data:
  execution_seconds: 1.639128618

```

Failed notebooks will not be cached, but the exception traceback will be added to the notebook's project record:

```console
$ jcache project show 2
ID: 2
URI: ../tests/notebooks/basic_failing.ipynb
Reader: nbformat
Created: 2021-08-02 03:12
Failed Last Execution!
Traceback (most recent call last):
  File "../jupyter_cache/executors/utils.py", line 55, in single_nb_execution
    record_timing=False,
  File "../.tox/create_cli_doc/lib/python3.7/site-packages/nbclient/client.py", line 1112, in execute
    return NotebookClient(nb=nb, resources=resources, km=km, **kwargs).execute()
  File "../.tox/create_cli_doc/lib/python3.7/site-packages/nbclient/util.py", line 74, in wrapped
    return just_run(coro(*args, **kwargs))
  File "../.tox/create_cli_doc/lib/python3.7/site-packages/nbclient/util.py", line 53, in just_run
    return loop.run_until_complete(coro)
  File "../.tox/create_cli_doc/lib/python3.7/asyncio/base_events.py", line 587, in run_until_complete
    return future.result()
  File "../.tox/create_cli_doc/lib/python3.7/site-packages/nbclient/client.py", line 554, in async_execute
    cell, index, execution_count=self.code_cells_executed + 1
  File "../.tox/create_cli_doc/lib/python3.7/site-packages/nbclient/client.py", line 857, in async_execute_cell
    self._check_raise_for_error(cell, exec_reply)
  File "../.tox/create_cli_doc/lib/python3.7/site-packages/nbclient/client.py", line 760, in _check_raise_for_error
    raise CellExecutionError.from_cell_and_msg(cell, exec_reply_content)
nbclient.exceptions.CellExecutionError: An error occurred while executing the following cell:
------------------
raise Exception('oopsie!')
------------------

---------------------------------------------------------------------------
Exception                                 Traceback (most recent call last)
/var/folders/t2/xbl15_3n4tsb1vr_ccmmtmbr0000gn/T/ipykernel_86857/340246212.py in <module>
----> 1 raise Exception('oopsie!')

Exception: oopsie!
Exception: oopsie!


```

```{tip}
Code cells can be tagged with `raises-exception` to let the executor known that a cell *may* raise an exception
(see [this issue on its behaviour](https://github.com/jupyter/nbconvert/issues/730)).
```

Once executed you may leave notebooks in the project, for later re-execution, or remove them:

```console
$ jcache project clear
Are you sure you want to permanently clear the project!? [y/N]: y
Project cleared!
```

You can also add notebooks to the projects with assets;
external files that are required by the notebook during execution.
As with artefacts, these files must be in the same folder as the notebook,
or a sub-folder.

```console
$ jcache project add-with-assets -nb tests/notebooks/basic.ipynb tests/notebooks/artifact_folder/artifact.txt
Success!
```

```console
$ jcache project show 1
ID: 1
URI: ../tests/notebooks/basic.ipynb
Reader: nbformat
Created: 2021-08-02 03:12
Cache ID: 6
Assets:
- ../tests/notebooks/artifact_folder/artifact.txt
```
