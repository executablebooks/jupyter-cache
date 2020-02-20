"""This module defines the abstract interface of the cache.

API access to the cache should use this interface,
with no assumptions about the backend storage/retrieval mechanisms.
"""
from abc import ABC, abstractmethod
from typing import Optional, Set

import nbformat as nbf

NB_VERSION = 4


class CachingError(Exception):
    """An error to raise when adding to the cache fails."""

    pass


class RetrievalError(Exception):
    """An error to raise when retrieving from the cache fails."""

    pass


class JupyterCacheAbstract(ABC):
    """An abstract cache for storing pre/post executed notebooks."""

    @abstractmethod
    def stage_notebook_node(self, node: nbf.NotebookNode, uri: str):
        """Stage a single notebook to the cache."""
        pass

    def stage_notebook_file(self, path: str, uri: Optional[str] = None):
        """Stage a single notebook to the cache.

        If uri is None, then will be set as path.
        """
        notebook = nbf.read(path, NB_VERSION)
        return self.stage_notebook_node(notebook, uri or path)

    @abstractmethod
    def list_staged_notebooks(self) -> Set:
        """list staged notebook uri's in the cache."""
        pass

    @abstractmethod
    def list_committed_notebooks(self) -> Set:
        """list committed notebook uri's in the cache."""
        pass

    @abstractmethod
    def invalidate_notebook(self, uri: str):
        """Invalidate a notebook in the cache.

        This moves it from committed -> staged.
        """
        pass

    @abstractmethod
    def remove_notebook(self, uri: str):
        """Completely remove a single notebook from the cache."""
        pass

    @abstractmethod
    def get_committed_notebook(self, uri: str) -> nbf.NotebookNode:
        """Return a single notebook from the cache."""
        pass

    # @abstractmethod
    # def get_codecell(self, uri: str, index: int) -> nbf.NotebookNode:
    #     """Return the code cell from a particular notebook.

    #     NOTE: the index **only** refers to the list of code cells, e.g.
    #     `[codecell_0, textcell_1, codecell_2]`
    #     would map {0: codecell_0, 1: codecell_2}
    #     """
    #     pass
