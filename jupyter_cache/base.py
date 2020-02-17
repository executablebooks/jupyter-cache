from abc import ABC, abstractmethod

import nbformat as nbf


class JupyterCacheAbstract(ABC):
    """An abstract cache for code kernels, cells and outputs."""

    @abstractmethod
    def add_notebook_node(
        self, node: nbf.NotebookNode, uri: str, overwrite: bool = False
    ):
        pass

    def add_notebook_file(self, uri: str, overwrite: bool = False):
        notebook = nbf.read(uri, 4)
        return self.add_notebook_node(notebook, uri, overwrite)

    @abstractmethod
    def get_notebook(self, uri: str, with_outputs=True) -> nbf.NotebookNode:
        pass
