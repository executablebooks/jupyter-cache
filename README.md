[Install](#install) | [Example](#example-cli-usage) | [Contributing](#contributing)

# jupyter-cache

[![Build Status](https://travis-ci.org/ExecutableBookProject/jupyter-cache.svg?branch=master)](https://travis-ci.org/ExecutableBookProject/jupyter-cache)
[![Coverage Status](https://coveralls.io/repos/github/ExecutableBookProject/jupyter-cache/badge.svg?branch=master)](https://coveralls.io/github/ExecutableBookProject/jupyter-cache?branch=master)

A defined interface for working with a cache of jupyter notebooks.

NOTE: This package is in an Alpha stage and liable to change.

Some desired requirements (not yet all implemented):

- Persistent
- Separates out "edits to content" from "edits to code cells". Cell
  rearranges and code cell changes should require a re-execution. Content changes should not.
- Allow parallel access to of notebooks (for execution)
- Store execution statistics/reports
- Store external assets: Notebooks being executed often require external assets: importing scripts/data/etc. These are prepared by the users.
- Store execution artifacts: created during exeution
- A transparent and robust cache invalidation: imagine the user updating an external dependency or a Python module, or checking out a different git branch.

## Install

```bash
pip install -e "git+https://github.com/ExecutableBookProject/jupyter-cache.git#egg=jupyter-cache[sphinx]"
```

For development:

```bash
git clone https://github.com/ExecutableBookProject/jupyter-cache
cd jupyter-cache
git checkout develop
pip install -e .[code_style,testing]
```

## Example API usage

to come ...

## Example CLI usage

From checked-out folder:

```console
$ jcache -h
Usage: jcache [OPTIONS] COMMAND [ARGS]...

  The command line interface of jupyter-cache.

Options:
  -v, --version     Show the version and exit.
  -p, --cache-path  Print the current cache path and exit.
  -h, --help        Show this message and exit.

Commands:
  cat-artifact    Print the contents of a commit artefact.
  clear           Clear the cache completely.
  commit-limit    Change the commit limit of the cache (default: 1000).
  commit-nb       Commit a notebook that has already been executed, with...
  commit-nbs      Commit notebook(s) that have already been executed.
  diff-nb         Print a diff of a notebook to one stored in the cache.
  execute         Execute outdated notebooks.
  list-commits    List committed notebook records in the cache.
  list-staged     List notebooks staged for possible execution.
  remove-commits  Remove notebook commit(s) from the cache by Primary Key.
  show-commit     Show details of a committed notebook in the cache.
  stage-nbs       Stage notebook(s) for execution.
  unstage-nbs     Unstage notebook(s) for execution.
```

You can commit notebooks straight into the cache. When committing, a check will be made that the notebooks look to have been executed correctly, i.e. the cell execution counts go sequentially up from 1.

```console
$ jcache commit-nbs tests/notebooks/basic.ipynb
Cache path: /Users/cjs14/GitHub/sandbox/.jupyter_cache
The cache does not yet exist, do you want to create it? [y/N]: y
Committing: /Users/cjs14/GitHub/sandbox/tests/notebooks/basic.ipynb
Validity Error: Expected cell 1 to have execution_count 1 not 2
The notebook may not have been executed, continue committing? [y/N]: y
Success!
```

Or to skip validation:

```console
$ jcache commit-nbs --no-validate tests/notebooks/*
Committing: /Users/cjs14/GitHub/sandbox/tests/notebooks/basic.ipynb
Committing: /Users/cjs14/GitHub/sandbox/tests/notebooks/basic_failing.ipynb
Committing: /Users/cjs14/GitHub/sandbox/tests/notebooks/basic_unrun.ipynb
Committing: /Users/cjs14/GitHub/sandbox/tests/notebooks/complex_outputs.ipynb
Success!
```

Once you've committed some notebooks, you can look at the 'commit records' for what has been cached:

```console
$ jcache list-commits --hashkeys
  PK  URI                    Created           Accessed          Hashkey
----  ---------------------  ----------------  ----------------  --------------------------------
   4  complex_outputs.ipynb  2020-02-23 20:33  2020-02-23 20:33  800c4a057730a55a384cfe579e3850aa
   3  basic_unrun.ipynb      2020-02-23 20:33  2020-02-23 20:33  818f3412b998fcf4fe9ca3cca11a3fc3
   2  basic_failing.ipynb    2020-02-23 20:33  2020-02-23 20:33  72859c2bf1e12f35f30ef131f0bef320
```

You can also commit with artefacts (external outputs of the notebook execution).

```console
$ jcache commit-nb -nb tests/notebooks/basic.ipynb tests/notebooks/artifact_folder/artifact.txt
Committing: /Users/cjs14/GitHub/jupyter-cache/tests/notebooks/basic.ipynb
Success!
```

```console
$ jcache show-commit 1
PK: 1
URI: /Users/cjs14/GitHub/jupyter-cache/tests/notebooks/basic.ipynb
Created: 2020-02-24 14:58
Accessed: 2020-02-24 14:58
Hashkey: 818f3412b998fcf4fe9ca3cca11a3fc3
Artifacts:
- artifact_folder/artifact.txt
```

```console
$ jcache cat-artifact 1 artifact_folder/artifact.txt
An artifact

```

These must be 'upstream' of the notebook folder:

```console
$ jcache commit-nb -nb tests/notebooks/basic.ipynb tests/test_db.py
Committing: /Users/cjs14/GitHub/jupyter-cache/tests/notebooks/basic.ipynb
Artifact Error: Path '/Users/cjs14/GitHub/jupyter-cache/tests/test_db.py' is not in folder '/Users/cjs14/GitHub/jupyter-cache/tests/notebooks''
```

Each notebook is hashed (code cells and kernel spec only), which is used to compare against 'staged' notebooks. Multiple hashes for the same URI can be added (the URI is just there for inspetion) and the size of the cache is limited (current default 1000) so that, at this size, the last accessed records begin to be deleted. You can remove cached records by the Primary Key (PK).

```console
$ jcache remove-commits 3
Removing PK = 3
Success!
```

You can also diff any of the commit records with any (external) notebook:

```console
$ jcache diff-nb 2 tests/notebooks/basic.ipynb
nbdiff
--- committed pk=2
+++ other: /Users/cjs14/GitHub/sandbox/tests/notebooks/basic.ipynb
## inserted before nb/cells/1:
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

## deleted nb/cells/1:
-  code cell:
-    source:
-      raise Exception('oopie')
```

If you stage some notebooks for execution, then you can list them to see which have existing records in the cache (by hash) and which will require execution:

```console
$ jcache stage-nbs tests/notebooks/*
Staging: /Users/cjs14/GitHub/sandbox/tests/notebooks/basic.ipynb
Staging: /Users/cjs14/GitHub/sandbox/tests/notebooks/basic_failing.ipynb
Staging: /Users/cjs14/GitHub/sandbox/tests/notebooks/basic_unrun.ipynb
Staging: /Users/cjs14/GitHub/sandbox/tests/notebooks/complex_outputs.ipynb
Success!
```

```console
$ jcache list-staged
  PK  URI                                    Created             Commit Pk
----  -------------------------------------  ----------------  -----------
   4  tests/notebooks/complex_outputs.ipynb  2020-02-23 20:48            4
   3  tests/notebooks/basic_unrun.ipynb      2020-02-23 20:48
   2  tests/notebooks/basic_failing.ipynb    2020-02-23 20:48            2
   1  tests/notebooks/basic.ipynb            2020-02-23 20:48
```

You can then run a basic execution of the required notebooks:

```console
$ jcache execute
Executing: /Users/cjs14/GitHub/sandbox/tests/notebooks/basic.ipynb
Success: /Users/cjs14/GitHub/sandbox/tests/notebooks/basic.ipynb
Executing: /Users/cjs14/GitHub/sandbox/tests/notebooks/basic_unrun.ipynb
Success: /Users/cjs14/GitHub/sandbox/tests/notebooks/basic_unrun.ipynb
Finished!
```

```console
$ jcache list-staged
  PK  URI                                    Created             Commit Pk
----  -------------------------------------  ----------------  -----------
   5  tests/notebooks/basic.ipynb            2020-02-23 20:57            5
   4  tests/notebooks/complex_outputs.ipynb  2020-02-23 20:48            4
   3  tests/notebooks/basic_unrun.ipynb      2020-02-23 20:48            5
   2  tests/notebooks/basic_failing.ipynb    2020-02-23 20:48            2
```

## Contributing

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

### Pull Requests

To contribute, make Pull Requests to the `develop` branch (this is the default branch). A PR can consist of one or multiple commits. Before you open a PR, make sure to clean up your commit history and create the commits that you think best divide up the total work as outlined above (use `git rebase` and `git commit --amend`). Ensure all commit messages clearly summarise the changes in the header and the problem that this commit is solving in the body.

Merging pull requests: There are three ways of 'merging' pull requests on GitHub:

- Squash and merge: take all commits, squash them into a single one and put it on top of the base branch.
    Choose this for pull requests that address a single issue and are well represented by a single commit.
    Make sure to clean the commit message (title & body)
- Rebase and merge: take all commits and 'recreate' them on top of the base branch. All commits will be recreated with new hashes.
    Choose this for pull requests that require more than a single commit.
    Examples: PRs that contain multiple commits with individually significant changes; PRs that have commits from different authors (squashing commits would remove attribution)
- Merge with merge commit: put all commits as they are on the base branch, with a merge commit on top
    Choose for collaborative PRs with many commits. Here, the merge commit provides actual benefits.
