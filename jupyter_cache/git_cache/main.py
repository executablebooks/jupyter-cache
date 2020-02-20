from contextlib import contextmanager
import io
from pathlib import Path
from typing import List, Optional

import git
import nbdime
import nbformat as nbf
import sqlalchemy as sqla

from jupyter_cache.base import (  # noqa: F401
    JupyterCacheAbstract,
    CachingError,
    RetrievalError,
    NB_VERSION,
)

from .db import OrmBase, OrmNotebook


class JupyterCacheGit(JupyterCacheAbstract):
    def __init__(self, path):
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

    def stage_notebook_node(self, node: nbf.NotebookNode, uri: str):
        """Stage a single notebook in the cache."""
        nb_path = self.get_notebook_path(uri)
        self.path.joinpath(nb_path).parent.mkdir(exist_ok=True)
        self.path.joinpath(nb_path).write_text(nbf.writes(node, NB_VERSION))
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
        self.repo.index.commit(message or "new commit", **kwargs)

    def commit_some(self, paths: List[str], message=None, **kwargs):
        """Commit some staged files."""
        # TODO for best way, awaiting answer from gitpython-developers/GitPython#985
        no_commit_paths = [
            d.b_path for d in self._list_staged() if d.b_path not in paths
        ]
        try:
            if no_commit_paths:
                self.repo.index.remove(no_commit_paths)
                # TODO this doesn't seem to work, since it causes the
                # the paths to be removed in the commit
            self.repo.index.commit(message or "new commit", **kwargs)
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

        This moves it from committed -> staged.
        """
        path = self.get_notebook_path(uri)
        # if path in self.list_staged_notebooks():
        #     return
        # TODO to invalidate should add {"invalidated": datatime}
        # to notebook.metadata or something like that
        text = self.path.joinpath(path).read_text()
        self.path.joinpath(path).write_text(text + " ")
        self.repo.index.add([str(path)])

    def remove_notebook(self, uri: str):
        """Completely remove a single notebook from the cache."""
        path = self.get_notebook_path(uri)
        # remove the entire folder
        folder = self.path.joinpath(path.parent)
        to_remove = [str(path.parent)] + [
            str(p.relative_to(self.path)) for p in folder.glob("**/*")
        ]
        self.repo.index.remove([str(folder)], True, r=True)
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

    def get_committed_notebook(self, uri: str) -> nbf.NotebookNode:
        path = self.get_notebook_path(uri)
        return nbf.reads(self._get_committed_text(path), NB_VERSION)

    def diff_staged_notebook(self, uri: str):
        path = self.get_notebook_path(uri)
        assert uri in self.list_staged_notebooks()
        staged_nb = nbf.reads(self.path.joinpath(path).read_text(), NB_VERSION)
        committed_nb = nbf.reads(self._get_committed_text(path), NB_VERSION)
        return nbdime.diff_notebooks(committed_nb, staged_nb)


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
