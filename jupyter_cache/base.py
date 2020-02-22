"""This module defines the abstract interface of the cache.

API access to the cache should use this interface,
with no assumptions about the backend storage/retrieval mechanisms.
"""
from abc import ABC, abstractmethod
from typing import Iterable, NamedTuple, Optional, Set

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

    def __init__(self, uri, message, *args, **kwargs):
        self.uri = uri
        super().__init__(message, *args, **kwargs)


class NbBundle(NamedTuple):
    """A container for notebooks and their associated data."""

    nb: nbf.NotebookNode
    uri: str
    assets = None


class JupyterCacheAbstract(ABC):
    """An abstract cache for storing pre/post executed notebooks."""

    @abstractmethod
    def clear_cache(self):
        """Clear the cache completely."""
        pass

    @abstractmethod
    def stage_notebook_bundle(self, bundle: NbBundle):
        """Stage a single notebook to the cache."""
        pass

    def stage_notebook_file(self, path: str, uri: Optional[str] = None):
        """Stage a single notebook to the cache.

        If uri is None, then will be set as path.
        """
        notebook = nbf.read(path, NB_VERSION)
        return self.stage_notebook_bundle(NbBundle(notebook, uri or path))

    @abstractmethod
    def get_staged_notebook(self, uri: str) -> NbBundle:
        """Return a single notebook from the cache."""
        pass

    @abstractmethod
    def list_staged_notebooks(self) -> Set:
        """list staged notebook uri's in the cache."""
        pass

    @abstractmethod
    def list_committed_notebooks(self) -> Set:
        """list committed notebook uri's in the cache."""
        pass

    @abstractmethod
    def remove_notebook(self, uri: str):
        """Completely remove a single notebook from the cache."""
        pass

    @abstractmethod
    def invalidate_notebook(self, uri: str):
        """Invalidate a notebook in the cache (making a staged copy)."""
        pass

    @abstractmethod
    def discard_staged_notebook(self, uri: str):
        """Discard any staged changes to a previously committed notebook."""
        pass

    @abstractmethod
    def diff_staged_notebook(self, uri: str, as_str=False, **kwargs):
        """Return a diff of a staged notebook to its committed counterpart."""
        pass

    @abstractmethod
    def commit_staged_notebook(self, uri: str, check_validity: bool = True):
        """Commit a staged notebook.

        If check_validity, then check that the notebook has been executed correctly,
        by asserting `execution_count`s are consecutive and start at 1
        """
        pass

    @abstractmethod
    def commit_all(self, message=None, **kwargs):
        """Commit all staged files."""
        pass

    @abstractmethod
    def get_committed_notebook(self, uri: str) -> NbBundle:
        """Return a single notebook from the cache."""
        pass

    @abstractmethod
    def get_committed_codecell(self, uri: str, index: int) -> nbf.NotebookNode:
        """Return a code cell from a committed notebook.

        NOTE: the index **only** refers to the list of code cells, e.g.
        `[codecell_0, textcell_1, codecell_2]`
        would map {0: codecell_0, 1: codecell_2}
        """
        pass

    @abstractmethod
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
        pass
