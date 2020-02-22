from contextlib import contextmanager
import copy
from datetime import datetime
import io
from pathlib import Path
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
    NB_VERSION,
)

from .db import OrmBase, OrmNotebook


class JupyterCacheGit(JupyterCacheAbstract):
    def __init__(self, path):
        # TODO limit stored commit depth
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

    def get_notebook_path(self, uri):
        """"Retrieve a relative path to a notebook, from its URI."""
        with self.db_session() as session:
            result = session.query(OrmNotebook.pk).filter_by(uri=uri).one_or_none()
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

    def _list_staged(self, create_patch=False):
        """Create a diff of the last commit, to the current working folder.

        Note: does not include untracked files.
        """
        # return self.repo.untracked_files
        # this lists modified + staged
        # return self.repo.head.commit.diff(None, create_patch=create_patch)
        # This lists modified but not staged
        # return self.repo.index.diff("HEAD", create_patch=create_patch)
        # This lists staged
        return self.repo.index.diff("HEAD", create_patch=create_patch)

    def list_staged_notebooks(self):
        """list staged notebook uri's in the cache."""
        return {
            self.get_notebook_uri(diff.a_path)
            for diff in self._list_staged()
            if Path(diff.a_path).name == "base.ipynb"
        }

    def commit_all(self, message=None, **kwargs):
        """Commit all staged files."""
        try:
            self.repo.index.commit(message or "new commit", **kwargs)
        except Exception as err:
            raise CachingError(err)

    def commit_some(self, paths: List[str], message=None, **kwargs):
        """Commit some staged files."""
        # TODO for best way, awaiting answer from:
        # https://github.com/gitpython-developers/GitPython/issues/985
        no_commit_paths = [
            d.b_path for d in self._list_staged() if d.b_path not in paths
        ]
        try:
            if no_commit_paths:
                self.repo.index.remove(no_commit_paths, working_tree=False)
                # TODO this doesn't seem to work, since it causes the
                # the no_commit_paths to be removed in the commit
            self.repo.index.commit(message or "new commit", **kwargs)
        except Exception as err:
            raise CachingError(err)
        finally:
            if no_commit_paths:
                self.repo.index.add(no_commit_paths)

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
        path = self.get_notebook_path(uri)
        nb = nbf.read(str(self.path.joinpath(path)), NB_VERSION)
        nb.metadata["invalidated"] = datetime.utcnow().isoformat()
        self.stage_notebook_bundle(NbBundle(nb, uri))

    def remove_notebook(self, uri: str):
        """Completely remove a single notebook from the cache."""
        path = self.get_notebook_path(uri)
        # remove the entire folder
        folder = self.path.joinpath(path.parent)
        to_remove = [str(path.parent)] + [
            str(p.relative_to(self.path)) for p in folder.glob("**/*")
        ]
        try:
            self.repo.index.remove([str(folder)], True, r=True)
        except Exception as err:
            raise CachingError(err)
        self.commit_some(to_remove, "remove notebook")

    def _get_committed_text(self, rel_path: str, encoding="utf8"):
        """Get the file content of a committed path."""
        try:
            blob = self.repo.head.commit.tree / str(rel_path)
        except KeyError as error:
            raise RetrievalError(str(error))
        stream = io.BytesIO()
        blob.stream_data(stream)
        return stream.getvalue().decode(encoding)

    def get_staged_notebook(self, uri: str) -> NbBundle:
        path = self.get_notebook_path(uri)
        # TODO optionally include assets
        # TODO test if staged?
        return NbBundle(
            nbf.reads(self.path.joinpath(path).read_text(), NB_VERSION), uri
        )

    def get_committed_notebook(self, uri: str) -> NbBundle:
        path = self.get_notebook_path(uri)
        # TODO optionally include assets
        return NbBundle(nbf.reads(self._get_committed_text(path), NB_VERSION), uri)

    def diff_staged_notebook(self, uri: str, as_str=False, **kwargs):
        assert uri in self.list_staged_notebooks()
        staged_nb = self.get_staged_notebook(uri).nb
        committed_nb = self.get_committed_notebook(uri).nb
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
        # TODO include invalidated notebooks
        # TODO deal with changes to assets
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
    path: str, description: Optional[str] = None, initial_commit=True
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
