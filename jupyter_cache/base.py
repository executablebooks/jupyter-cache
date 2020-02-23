"""This module defines the abstract interface of the cache.

API access to the cache should use this interface,
with no assumptions about the backend storage/retrieval mechanisms.
"""
from abc import ABC, abstractmethod
from typing import NamedTuple, Optional

import nbformat as nbf

NB_VERSION = 4


class CachingError(Exception):
    """An error to raise when adding to the cache fails."""


class RetrievalError(Exception):
    """An error to raise when retrieving from the cache fails."""


class NbValidityError(Exception):
    """Signals a notebook may not be valid to commit.

    For example, because it has not yet been executed.
    """

    def __init__(self, message, nb_bundle, *args, **kwargs):
        self.uri = nb_bundle.uri
        super().__init__(message, *args, **kwargs)


class NbBundleIn(NamedTuple):
    """A container for notebooks and their associated data to commit."""

    nb: nbf.NotebookNode
    uri: str
    # assets = None


class NbBundleOut(NamedTuple):
    """A container for notebooks and their associated data that have been executed."""

    nb: nbf.NotebookNode
    commit: dict
    # artifacts = None


class JupyterCacheAbstract(ABC):
    """An abstract cache for storing pre/post executed notebooks."""

    @abstractmethod
    def clear_cache(self):
        """Clear the cache completely."""
        pass

    @abstractmethod
    def commit_notebook_bundle(
        self, bundle: NbBundleIn, check_validity: bool = True, overwrite: bool = False
    ) -> int:
        """Commit an executed notebook, returning its primary key.

        If check_validity, then check that the notebook has been executed correctly,
        by asserting `execution_count`s are consecutive and start at 1
        """
        pass

    def commit_notebook_file(
        self,
        path: str,
        uri: Optional[str] = None,
        check_validity: bool = True,
        overwrite: bool = False,
    ) -> int:
        """Commit an executed notebook, returning its primary key.

        If check_validity, then check that the notebook has been executed correctly,
        by asserting `execution_count`s are consecutive and start at 1.
        """
        notebook = nbf.read(path, NB_VERSION)
        return self.commit_notebook_bundle(
            NbBundleIn(notebook, uri or path),
            check_validity=check_validity,
            overwrite=overwrite,
        )

    @abstractmethod
    def list_commit_records(self) -> list:
        """Return a list of committed notebook records."""
        pass

    def get_commit_record(self, pk: int) -> dict:
        """Return the record of a commit, by its primary key"""
        pass

    @abstractmethod
    def get_commit_bundle(self, pk: int) -> NbBundleOut:
        """Return an executed notebook bundle, by its primary key"""
        pass

    @abstractmethod
    def get_commit_codecell(self, uri: str, index: int) -> nbf.NotebookNode:
        """Return a code cell from a committed notebook.

        NOTE: the index **only** refers to the list of code cells, e.g.
        `[codecell_0, textcell_1, codecell_2]`
        would map {0: codecell_0, 1: codecell_2}
        """
        pass

    @abstractmethod
    def match_commit_notebook(self, nb: nbf.NotebookNode) -> int:
        """Match an executed notebook, returning its primary key"""
        pass

    def match_commit_file(self, path: str) -> int:
        """Match an executed notebook, returning its primary key"""
        notebook = nbf.read(path, NB_VERSION)
        return self.match_commit_notebook(notebook)

    @abstractmethod
    def diff_nbnode_with_commit(
        self, pk: int, nb: nbf.NotebookNode, uri: str = "", as_str=False, **kwargs
    ):
        """Return a diff of a notebook to a committed one."""
        pass

    def diff_nbfile_with_commit(self, pk: int, path: str, as_str=False, **kwargs):
        """Return a diff of a notebook to a committed one."""
        nb = nbf.read(path, NB_VERSION)
        return self.diff_nbnode_with_commit(pk, nb, uri=path, as_str=as_str, **kwargs)

    @abstractmethod
    def stage_notebook_file(self, uri: str):
        """Stage a single notebook for execution."""
        pass

    @abstractmethod
    def discard_staged_notebook(self, uri: str):
        """Discard a staged notebook."""
        pass

    @abstractmethod
    def list_staged_records(self) -> list:
        """list staged notebook uri's in the cache."""
        pass

    @abstractmethod
    def get_staged_notebook(self, uri: str) -> NbBundleIn:
        """Return a single notebook from the cache."""
        pass

    @abstractmethod
    def list_nbs_to_exec(self) -> list:
        """List staged notebooks, whose hash is not present in the cache commits."""
        pass
