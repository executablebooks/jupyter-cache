from abc import ABC, abstractmethod
from typing import Set

import nbformat as nbf

NB_VERSION = 4


class CacheError(Exception):
    pass


class JupyterCacheAbstract(ABC):
    """An abstract cache for code kernels, cells and outputs."""

    @abstractmethod
    def add_notebook_node(
        self, node: nbf.NotebookNode, uri: str, overwrite: bool = False
    ):
        """Add a single notebook to the cache."""
        pass

    def add_notebook_file(self, uri: str, overwrite: bool = False):
        """Add a single notebook to the cache."""
        notebook = nbf.read(uri, NB_VERSION)
        return self.add_notebook_node(notebook, uri, overwrite)

    @abstractmethod
    def get_notebook(self, uri: str, with_outputs: bool = True) -> nbf.NotebookNode:
        """Get a single notebook from the cache.

        If `with_outputs` is False, return with all outputs removed.
        """
        pass

    @abstractmethod
    def remove_notebook(self, uri: str) -> nbf.NotebookNode:
        """Remove a single notebook from the cache."""
        pass

    @abstractmethod
    def list_notebooks(self) -> Set[str]:
        """list the notebook uri's in the cache."""
        pass
