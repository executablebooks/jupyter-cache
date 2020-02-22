from contextlib import contextmanager
import copy
from datetime import datetime
import io
from pathlib import Path
from shutil import rmtree
from typing import Iterable, List, Optional

import git
import nbdime
import nbformat as nbf
from nbdime.prettyprint import pretty_print_diff, PrettyPrintConfig
import sqlalchemy as sqla

from jupyter_cache.base import (  # noqa: F401
    JupyterCacheAbstract,
    NbBundle,
    CachingError,
    RetrievalError,
    NbValidityError,
    NB_VERSION,
)

from .db import OrmBase, OrmNotebook


class JupyterCacheGit(JupyterCacheAbstract):
    def __init__(self, path):
        # TODO limit stored commit depth, or have option to reset it
        # see https://stackoverflow.com/a/26000395/5033292
        # https://www.perforce.com/blog/vcs/git-beyond-basics-using-shallow-clones
        self._repo = get_or_create_repo(path, "A repository to cache Jupyter notebooks")
        self._db = None

    @property
    def repo(self):
        return self._repo

    @property
    def path(self):
        return Path(self._repo.working_dir)

    @property
    def db(self):
        """a simple database for storing persistent global data."""
        if self._db is None:
            self._db = sqla.create_engine("sqlite:///{}".format(self.path / "main.db"))
            OrmBase.metadata.create_all(self._db)
        return self._db

    @contextmanager
    def db_session(self):
        """Open a connection to the database."""
        session = sqla.orm.sessionmaker(bind=self.db)()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def __getstate__(self):
        """For pickling instances, db must be removed."""
        state = self.__dict__.copy()
        state["_db"] = None
        return state

    def clear_cache(self):
        """Clear the cache completely."""
        path = str(self.path.absolute())
        rmtree(self.path)
        self._repo = get_or_create_repo(path, "A repository to cache Jupyter notebooks")
        self._db = None

    def get_notebook_path(self, uri, raise_on_missing=False):
        """"Retrieve a relative path to a notebook, from its URI."""
        with self.db_session() as session:
            result = session.query(OrmNotebook.pk).filter_by(uri=uri).one_or_none()
            if result is None and raise_on_missing:
                raise RetrievalError("URI not in cache: {}".format(uri))
            if result is None:
                nb = OrmNotebook(uri=uri)
                session.add(nb)
                session.commit()
                session.refresh(nb)
                pk = nb.pk
            else:
                pk = result[0]
        return Path(f"notebook_{pk}", "base.ipynb")

    def get_notebook_uri(self, path):
        """"Retrieve a notebook URI, from its relative path."""
        pk = int(Path(path).parent.name.replace("notebook_", ""))
        with self.db_session() as session:
            uri = session.query(OrmNotebook.uri).filter_by(pk=pk).one_or_none()
        if uri is None:
            raise KeyError(path)
        return uri[0]

    def stage_notebook_bundle(self, bundle: NbBundle):
        """Stage a single notebook in the cache."""
        # optionally include assets (also concept of global assets?)
        nb_path = self.get_notebook_path(bundle.uri)
        self.path.joinpath(nb_path).parent.mkdir(exist_ok=True)
        self.path.joinpath(nb_path).write_text(nbf.writes(bundle.nb, NB_VERSION))
        self.repo.index.add([str(nb_path)])

    def _list_staged(self, create_patch=False, no_renames=True):
        """Create a diff of the last commit, to the current working folder.

        Note: does not include untracked files.
        """
        # TODO think more about renames, we default to --no-renames because
        # we don't want git thinking a deleted notebook uri and different added uri
        # are the same, renamed, file. But this would get trickier for renamed assets.

        # return self.repo.untracked_files
        # this lists modified + staged
        # return self.repo.head.commit.diff(
        #   None, create_patch=create_patch, no_renames=no_renames)
        # This lists modified but not staged
        # return self.repo.index.diff(
        #   "HEAD", create_patch=create_patch, no_renames=no_renames)
        # This lists staged
        return self.repo.index.diff(
            "HEAD", create_patch=create_patch, no_renames=no_renames
        )

    def list_staged_notebooks(self):
        """list staged notebook uri's in the cache."""
        return {
            self.get_notebook_uri(diff.a_path)
            for diff in self._list_staged()
            if Path(diff.a_path).name == "base.ipynb"
        }

    def commit_all(self, message=None, **kwargs):
        """Commit all staged files."""
        # TODO commit tag option
        try:
            self.repo.index.commit(message or "new commit", **kwargs)
        except Exception as err:
            raise CachingError(err)

    def _commit_some(self, paths: List[str], message=None, **kwargs):
        """Commit some staged files."""
        # TODO commit tag option
        # TODO for best way, awaiting answer from:
        # https://github.com/gitpython-developers/GitPython/issues/985
        if not paths:
            return
        if isinstance(paths, str):
            paths = [paths]
        try:
            self.repo.git.commit(
                *paths,
                only=True,
                message=message or "new commit",
                no_edit=True,
                **kwargs,
            )
        except git.GitCommandError as err:
            raise CachingError(err)

    def list_committed_notebooks(self):
        """list committed notebook uri's in the cache."""
        return {
            self.get_notebook_uri(path)
            for path in list_files_in_commit(self.repo.head.commit)
            if Path(path).name == "base.ipynb"
        }

    def invalidate_notebook(self, uri: str):
        """Invalidate a notebook in the cache.

        This adds an 'invalidated' key to the notebook's metadata
        with the current datetime.
        """
        path = self.get_notebook_path(uri, raise_on_missing=True)
        nb = nbf.read(str(self.path.joinpath(path)), NB_VERSION)
        nb.metadata["invalidated"] = datetime.utcnow().isoformat()
        self.stage_notebook_bundle(NbBundle(nb, uri))

    def remove_notebook(self, uri: str):
        """Completely remove a single notebook from the cache."""
        path = self.get_notebook_path(uri, raise_on_missing=True)
        # remove the entire folder
        folder = self.path.joinpath(path.parent)
        to_remove = [str(path.parent)] + [
            str(p.relative_to(self.path)) for p in folder.glob("**/*")
        ]
        try:
            self.repo.index.remove([str(folder)], True, r=True)
        except Exception as err:
            raise CachingError(err)
        self._commit_some(to_remove, "remove notebook")
        # TODO remove uri from global database

    def discard_staged_notebook(self, uri: str):
        """Discard any staged changes to a previously committed notebook."""
        path = self.get_notebook_path(uri, raise_on_missing=True)
        try:
            self.repo.git.checkout("HEAD", "--", str(path))
        except git.GitCommandError as err:
            raise CachingError(err)

    def _get_committed_text(self, uri: str, rel_path: str, encoding="utf8"):
        """Get the file content of a committed path."""
        try:
            blob = self.repo.head.commit.tree / str(rel_path)
        except KeyError:
            raise RetrievalError("No committed: {}".format(uri))
        stream = io.BytesIO()
        blob.stream_data(stream)
        return stream.getvalue().decode(encoding)

    def get_staged_notebook(self, uri: str) -> NbBundle:
        if uri not in self.list_staged_notebooks():
            raise RetrievalError("URI not in staged list: {}".format(uri))
        path = self.get_notebook_path(uri, raise_on_missing=True)
        if not self.path.joinpath(path).exists():
            raise RetrievalError("URI does not exist in cache: {}".format(uri))
        # TODO optionally include assets
        return NbBundle(
            nbf.reads(self.path.joinpath(path).read_text(), NB_VERSION), uri
        )

    def get_committed_notebook(self, uri: str) -> NbBundle:
        path = self.get_notebook_path(uri, raise_on_missing=True)
        # TODO optionally include assets
        # TODO cache notebook reads in memory (when retrieving from this cache,
        # should check that the cache represents the last commit)
        # this will be important when adding queries for specific cell outputs
        return NbBundle(nbf.reads(self._get_committed_text(uri, path), NB_VERSION), uri)

    def get_committed_codecell(self, uri: str, index: int) -> nbf.NotebookNode:
        """Return the code cell from a committed notebook.

        NOTE: the index **only** refers to the list of code cells, e.g.
        `[codecell_0, textcell_1, codecell_2]`
        would map {0: codecell_0, 1: codecell_2}
        """
        nb_bundle = self.get_committed_notebook(uri)
        _code_index = 0
        for cell in nb_bundle.nb.cells:
            if cell.cell_type != "code":
                continue
            if _code_index == index:
                return cell
            _code_index += 1
        raise RetrievalError(f"Notebook contains less than {index+1} code cell(s)")

    def commit_staged_notebook(self, uri: str, check_validity: bool = True):
        """Commit a staged notebook.

        If check_validity, then check that the notebook has been executed correctly,
        by asserting `execution_count`s are consecutive and start at 1
        """
        nb_bundle = self.get_staged_notebook(uri)
        if check_validity:
            execution_count = 1
            for i, cell in enumerate(nb_bundle.nb.cells):
                if cell.cell_type != "code":
                    continue
                if cell.execution_count != execution_count:
                    raise NbValidityError(
                        uri,
                        "Expected cell {} to have execution_count {} not {}".format(
                            i, execution_count, cell.execution_count
                        ),
                    )
                execution_count += 1
                # TODO check for output exceptions?
        # TODO assets
        path = self.get_notebook_path(uri)
        self._commit_some([path], message="committing {}".format(uri))

    def diff_staged_notebook(self, uri: str, as_str=False, **kwargs):
        """Return a diff of a staged notebook to its committed counterpart."""
        committed_nb = self.get_committed_notebook(uri).nb
        if uri not in self.list_staged_notebooks():
            staged_nb = committed_nb
        else:
            staged_nb = self.get_staged_notebook(uri).nb
        diff = nbdime.diff_notebooks(committed_nb, staged_nb)
        if not as_str:
            return diff
        stream = io.StringIO()
        stream.writelines(
            ["nbdiff {uri}\n".format(uri=uri), "--- committed\n", "+++ staged\n"]
        )
        pretty_print_diff(
            committed_nb, diff, "nb", PrettyPrintConfig(out=stream, **kwargs)
        )
        return stream.getvalue()

    def iter_notebooks_to_exec(
        self, compare_nb_meta=("kernelspec", "invalidated"), compare_cell_meta=None
    ) -> Iterable[NbBundle]:
        """Iterate through notebooks that require re-execution.

        These are staged notebooks that have not previously been committed or,
        compared to their committed version, have:

        - Modified metadata
          (only comparing keys listed in compare_nb_meta or all if None).
        - A different number of code cells.
        - Modified at least one code cells metadata
          (only comparing keys listed in compare_cell_meta or all if None).
        - Modified at least one code cells source code.

        """
        # TODO deal with changes to assets?
        for uri in self.list_staged_notebooks():
            # get notebooks
            staged_nb = self.get_staged_notebook(uri).nb
            try:
                committed_nb = self.get_committed_notebook(uri).nb
            except RetrievalError:
                # no committed notebook so requires execution
                yield NbBundle(staged_nb, uri)
                continue
            # get copy for diffing
            staged_nb_copy = copy.deepcopy(staged_nb)
            # extract only required notebook component for diffing
            for nb in [staged_nb_copy, committed_nb]:
                nb.metadata = nbf.from_dict(
                    {
                        k: v
                        for k, v in nb.metadata.items()
                        if (k in compare_nb_meta) or compare_nb_meta is None
                    }
                )
                diff_cells = []
                for cell in nb.cells:
                    if cell.cell_type != "code":
                        continue
                    diff_cell = nbf.from_dict(
                        {
                            "cell_type": cell.cell_type,
                            "source": cell.source,
                            "metadata": {
                                k: v
                                for k, v in cell.metadata.items()
                                if (k in compare_cell_meta) or compare_cell_meta is None
                            },
                            "execution_count": None,
                            "outputs": [],
                        }
                    )
                    diff_cells.append(diff_cell)
                nb.cells = diff_cells
            if nbdime.diff_notebooks(staged_nb_copy, committed_nb):
                # If their is a diff then yield
                yield NbBundle(staged_nb, uri)


def get_or_create_repo(
    path: str, description: Optional[str] = None, initial_commit=True, clean=True
) -> git.Repo:
    """Get of create a new repository.

    By default we make an initial (empty) commit,
    so that we can diff against for added files.
    """
    try:
        repo = git.Repo(path)
    except git.NoSuchPathError:
        repo = git.Repo.init(path, mkdir=True)
        if description:
            repo.description = description
        if initial_commit:
            repo.index.commit("initial commit")
    except git.InvalidGitRepositoryError:
        repo = git.Repo.init(path, mkdir=True)
        if description:
            repo.description = description
        if initial_commit:
            repo.index.commit("initial commit")
    if clean:
        # Cleanup unnecessary files and optimize the local repository
        # --auto does this in a more efficient/approximate manner
        repo.git.gc(auto=True)
    return repo


def list_files_in_commit(commit):
    """Lists all the files in a repo at a given commit

    :param commit: A gitpython Commit object
    """
    file_list = []
    stack = [commit.tree]
    while len(stack) > 0:
        tree = stack.pop()
        for b in tree.blobs:
            file_list.append(b.path)
        for subtree in tree.trees:
            stack.append(subtree)
    return file_list


def get_commit_changes(commit):
    return commit.stats.files
