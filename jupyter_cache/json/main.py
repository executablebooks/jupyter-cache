import pathlib
from typing import Set

from jupyter_cache.base import (
    JupyterCacheAbstract,
    CachingError,
    RetrievalError,
    NB_VERSION,
)

import nbformat as nbf
from tinydb import TinyDB, Query
from tinydb.database import Table

from .utils import CacheDict


class JupyterCacheJson(JupyterCacheAbstract):
    """A JSON based database cache for code kernels, cells, outputs, etc."""

    def __init__(self, db_folder_path: str, cache_nbs: int = 1):
        self._path = pathlib.Path(db_folder_path) / "jupyter_cache"
        self._db = TinyDB(self.path / "db.json")
        # this cache makes it more efficient to retrieve notebook multiple times,
        # by storing a limited number in memory
        self._nbcache = CacheDict(cache_nbs)

    @property
    def path(self) -> pathlib.Path:
        if not self._path.exists():
            self._path.mkdir(parents=True, exist_ok=True)
        return self._path

    def _get_nb_path(self, doc_id) -> pathlib.Path:
        return self.path / f"{doc_id}.ipynb"

    @property
    def db(self):
        # TODO access with context manager
        return self._db

    def _doc_table(self) -> Table:
        return self.db.table("documents")

    def add_notebook_node(
        self, node: nbf.NotebookNode, uri: str, overwrite: bool = False
    ):
        """Add a single notebook to the cache."""
        table = self._doc_table()
        if table.contains(Query().uri == uri) and not overwrite:
            raise CachingError(f"document already exists: {uri}")
        (doc_id,) = table.upsert({"uri": uri}, Query().uri == uri)
        self._get_nb_path(doc_id).write_text(nbf.writes(node, NB_VERSION))
        self._nbcache[uri] = node

    def get_notebook(self, uri: str, with_outputs=True) -> nbf.NotebookNode:
        """Get a single notebook from the cache.

        If `with_outputs` is False, return with all outputs removed.
        """
        table = self._doc_table()
        record = table.get(Query().uri == uri)
        if record is None:
            raise RetrievalError(uri)
        if uri in self._nbcache:
            nb = self._nbcache[uri]
        else:
            nb = nbf.reads(self._get_nb_path(record.doc_id).read_text(), NB_VERSION)
            self._nbcache[uri] = nb
        if with_outputs:
            return nb
        for cell in nb.cells:
            if cell.cell_type == "code":
                cell.outputs = []
        return nb

    def remove_notebook(self, uri: str) -> nbf.NotebookNode:
        """Remove a single notebook from the cache."""
        table = self._doc_table()
        record = table.get(Query().uri == uri)
        if record is None:
            return
        if self._get_nb_path(record.doc_id).exists():
            self._get_nb_path(record.doc_id).unlink()
        table.remove(Query().uri == uri)
        self._nbcache.pop(uri)

    def list_notebooks(self) -> Set[str]:
        """list the notebook uri's in the cache."""
        table = self._doc_table()
        return {result["uri"] for result in table.all()}

    def get_codecell(self, uri: str, index: int) -> nbf.NotebookNode:
        """Return the code cell from a particular notebook.

        NOTE: the index **only** refers to the list of code cells, e.g.
        `[codecell_0, textcell_1, codecell_2]` would map {0: codecell_0, 1: codecell_2}
        """
        nb = self.get_notebook(uri)
        _code_index = 0
        for cell in nb.cells:
            if cell.cell_type != "code":
                continue
            if _code_index == index:
                return cell
            _code_index += 1
        raise RetrievalError(f"notebook contains less than {index+1} code cell(s)")
