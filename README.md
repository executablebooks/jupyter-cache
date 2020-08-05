[Install](#install) | [Example](#example-cli-usage) | [Contributing](#contributing)

# jupyter-cache

[![CI Status][travis-badge]][travis-link]
[![Coverage][coveralls-badge]][coveralls-link]
[![Documentation Status][rtd-badge]][rtd-link]
[![Code style: black][black-badge]][black-link]
[![PyPI][pypi-badge]][pypi-link]

A defined interface for working with a cache of jupyter notebooks.

NOTE: This package is in an Alpha stage and liable to change.

Some desired requirements (not yet all implemented):

- Persistent
- Separates out "edits to content" from "edits to code cells". Cell
  rearranges and code cell changes should require a re-execution. Content changes should not.
- Allow parallel access to notebooks (for execution)
- Store execution statistics/reports
- Store external assets: Notebooks being executed often require external assets: importing scripts/data/etc. These are prepared by the users.
- Store execution artifacts: created during exeution
- A transparent and robust cache invalidation: imagine the user updating an external dependency or a Python module, or checking out a different git branch.

[travis-badge]: https://travis-ci.org/ExecutableBookProject/jupyter-cache.svg?branch=master
[travis-link]: https://travis-ci.org/ExecutableBookProject/jupyter-cache
[coveralls-badge]: https://coveralls.io/repos/github/ExecutableBookProject/jupyter-cache/badge.svg?branch=master
[coveralls-link]: https://coveralls.io/github/ExecutableBookProject/jupyter-cache?branch=master
[rtd-badge]: https://readthedocs.org/projects/jupyter-cache/badge/?version=latest
[rtd-link]: https://jupyter-cache.readthedocs.io/en/latest/?badge=latest
[black-badge]: https://img.shields.io/badge/code%20style-black-000000.svg
[pypi-badge]: https://img.shields.io/pypi/v/jupyter-cache.svg
[pypi-link]: https://pypi.org/project/jupyter-cache
[black-link]: https://github.com/ambv/black

## Install

```bash
pip install jupyter-cache[cli]
```

For development:

```bash
git clone https://github.com/ExecutableBookProject/jupyter-cache
cd jupyter-cache
git checkout develop
pip install -e .[cli,code_style,testing]
```

## Example API usage

to come ...

## Example CLI usage

<!-- This section was auto-generated on 2020-03-12 17:31 by: /Users/cjs14/GitHub/jupyter-cache/tests/make_cli_readme.py -->

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
  execute  Execute staged notebooks that are outdated.
  stage    Commands for staging notebooks to be executed.
```

**Important**: Execute this in the terminal for auto-completion:

```console
eval "$(_JCACHE_COMPLETE=source jcache)"
```

### Caching Executed Notebooks

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
which is used to compare against 'staged' notebooks.
Multiple hashes for the same URI can be added
(the URI is just there for inspetion) and the size of the cache is limited
(current default 1000) so that, at this size,
the last accessed records begin to be deleted.
You can remove cached records by their ID.

```console
$ jcache cache list
  ID  Origin URI                             Created           Accessed
----  -------------------------------------  ----------------  ----------------
   5  tests/notebooks/external_output.ipynb  2020-03-12 17:31  2020-03-12 17:31
   4  tests/notebooks/complex_outputs.ipynb  2020-03-12 17:31  2020-03-12 17:31
   3  tests/notebooks/basic_unrun.ipynb      2020-03-12 17:31  2020-03-12 17:31
   2  tests/notebooks/basic_failing.ipynb    2020-03-12 17:31  2020-03-12 17:31
```

Tip: Use the `--latest-only` option, to only show the latest versions of cached notebooks.

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
Created: 2020-03-12 17:31
Accessed: 2020-03-12 17:31
Hashkey: 818f3412b998fcf4fe9ca3cca11a3fc3
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

### Staging Notebooks for execution

```console
$ jcache stage --help
Usage: stage [OPTIONS] COMMAND [ARGS]...

  Commands for staging notebooks to be executed.

Options:
  --help  Show this message and exit.

Commands:
  add              Stage notebook(s) for execution.
  add-with-assets  Stage a notebook, with possible asset files.
  list             List notebooks staged for possible execution.
  remove-ids       Un-stage notebook(s), by ID.
  remove-uris      Un-stage notebook(s), by URI.
  show             Show details of a staged notebook.
```

Staged notebooks are recorded as pointers to their URI,
i.e. no physical copying takes place until execution time.

If you stage some notebooks for execution, then
you can list them to see which have existing records in the cache (by hash),
and which will require execution:

```console
$ jcache stage add tests/notebooks/basic.ipynb tests/notebooks/basic_failing.ipynb tests/notebooks/basic_unrun.ipynb tests/notebooks/complex_outputs.ipynb tests/notebooks/external_output.ipynb
Staging: ../tests/notebooks/basic.ipynb
Staging: ../tests/notebooks/basic_failing.ipynb
Staging: ../tests/notebooks/basic_unrun.ipynb
Staging: ../tests/notebooks/complex_outputs.ipynb
Staging: ../tests/notebooks/external_output.ipynb
Success!
```

```console
$ jcache stage list
  ID  URI                                    Created             Assets    Cache ID
----  -------------------------------------  ----------------  --------  ----------
   5  tests/notebooks/external_output.ipynb  2020-03-12 17:31         0           5
   4  tests/notebooks/complex_outputs.ipynb  2020-03-12 17:31         0
   3  tests/notebooks/basic_unrun.ipynb      2020-03-12 17:31         0           6
   2  tests/notebooks/basic_failing.ipynb    2020-03-12 17:31         0           2
   1  tests/notebooks/basic.ipynb            2020-03-12 17:31         0           6
```

You can remove a staged notebook by its URI or ID:

```console
$ jcache stage remove-ids 4
Unstaging ID: 4
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
Finished! Successfully executed notebooks have been cached.
succeeded:
- ../tests/notebooks/basic.ipynb
- ../tests/notebooks/basic_unrun.ipynb
excepted:
- ../tests/notebooks/basic_failing.ipynb
errored: []

```

Successfully executed notebooks will be cached to the cache,
along with any 'artefacts' created by the execution,
that are inside the notebook folder, and data supplied by the executor.

```console
$ jcache stage list
  ID  URI                                    Created             Assets    Cache ID
----  -------------------------------------  ----------------  --------  ----------
   5  tests/notebooks/external_output.ipynb  2020-03-12 17:31         0           5
   3  tests/notebooks/basic_unrun.ipynb      2020-03-12 17:31         0           6
   2  tests/notebooks/basic_failing.ipynb    2020-03-12 17:31         0
   1  tests/notebooks/basic.ipynb            2020-03-12 17:31         0           6
```

Execution data (such as execution time) will be stored in the cache record:

```console
$ jcache cache show 6
ID: 6
Origin URI: ../tests/notebooks/basic_unrun.ipynb
Created: 2020-03-12 17:31
Accessed: 2020-03-12 17:31
Hashkey: 818f3412b998fcf4fe9ca3cca11a3fc3
Data:
  execution_seconds: 1.0559415130000005

```

Failed notebooks will not be cached, but the exception traceback will be added to the stage record:

```console
$ jcache stage show 2
ID: 2
URI: ../tests/notebooks/basic_failing.ipynb
Created: 2020-03-12 17:31
Failed Last Execution!
Traceback (most recent call last):
  File "../jupyter_cache/executors/basic.py", line 152, in execute
    executenb(nb_bundle.nb, cwd=tmpdirname)
  File "/anaconda/envs/mistune/lib/python3.7/site-packages/nbconvert/preprocessors/execute.py", line 737, in executenb
    return ep.preprocess(nb, resources, km=km)[0]
  File "/anaconda/envs/mistune/lib/python3.7/site-packages/nbconvert/preprocessors/execute.py", line 405, in preprocess
    nb, resources = super(ExecutePreprocessor, self).preprocess(nb, resources)
  File "/anaconda/envs/mistune/lib/python3.7/site-packages/nbconvert/preprocessors/base.py", line 69, in preprocess
    nb.cells[index], resources = self.preprocess_cell(cell, resources, index)
  File "/anaconda/envs/mistune/lib/python3.7/site-packages/nbconvert/preprocessors/execute.py", line 448, in preprocess_cell
    raise CellExecutionError.from_cell_and_msg(cell, out)
nbconvert.preprocessors.execute.CellExecutionError: An error occurred while executing the following cell:
------------------
raise Exception('oopsie!')
------------------

---------------------------------------------------------------------------
Exception                                 Traceback (most recent call last)
<ipython-input-1-714b2b556897> in <module>
----> 1 raise Exception('oopsie!')

Exception: oopsie!
Exception: oopsie!


```

Once executed you may leave staged notebooks, for later re-execution, or remove them:

```console
$ jcache stage remove-ids --all
Are you sure you want to remove all? [y/N]: y
Unstaging ID: 1
Unstaging ID: 2
Unstaging ID: 3
Unstaging ID: 5
Success!
```

You can also stage notebooks with assets;
external files that are required by the notebook during execution.
As with artefacts, these files must be in the same folder as the notebook,
or a sub-folder.

```console
$ jcache stage add-with-assets -nb tests/notebooks/basic.ipynb tests/notebooks/artifact_folder/artifact.txt
Success!
```

```console
$ jcache stage show 1
ID: 1
URI: ../tests/notebooks/basic.ipynb
Created: 2020-03-12 17:31
Cache ID: 6
Assets:
- ../tests/notebooks/artifact_folder/artifact.txt
```

## Contributing

jupyter-cache follows the [Executable Book Contribution Guide](https://executablebooks.org/en/latest/contributing.html). We'd love your help!

### Code Style

Code style is tested using [flake8](http://flake8.pycqa.org),
with the configuration set in `.flake8`,
and code formatted with [black](https://github.com/ambv/black).

Installing with `jupyter-cache[code_style]` makes the [pre-commit](https://pre-commit.com/)
package available, which will ensure this style is met before commits are submitted, by reformatting the code
and testing for lint errors.
It can be setup by:

```shell
>> cd jupyter-cache
>> pre-commit install
```

Optionally you can run `black` and `flake8` separately:

```shell
>> black .
>> flake8 .
```

Editors like VS Code also have automatic code reformat utilities, which can adhere to this standard.
