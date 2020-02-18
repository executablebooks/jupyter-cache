import pathlib

from jupyter_cache.base import JupyterCacheAbstract, CacheError, NB_VERSION

import nbformat as nbf
from tinydb import TinyDB, Query
from tinydb.database import Table


class JupyterCacheJson(JupyterCacheAbstract):
    """A JSON based database cache for code kernels, cells, outputs, etc."""

    def __init__(self, db_folder_path: str):
        self._path = pathlib.Path(db_folder_path) / "jupyter_cache"
        self._db = TinyDB(self.path / "db.json")

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
        table = self._doc_table()
        if table.contains(Query().uri == uri) and not overwrite:
            raise CacheError(f"document already exists: {uri}")
        doc_id, = table.upsert({"uri": uri}, Query().uri == uri)
        self._get_nb_path(doc_id).write_text(nbf.writes(node, NB_VERSION))

    def get_notebook(self, uri: str, with_outputs=True) -> nbf.NotebookNode:
        table = self._doc_table()
        record = table.get(Query().uri == uri)
        if record is None:
            raise CacheError(uri)
        return nbf.reads(self._get_nb_path(record.doc_id).read_text(), NB_VERSION)

    def remove_notebook(self, uri: str) -> nbf.NotebookNode:
        table = self._doc_table()
        record = table.get(Query().uri == uri)
        if record is None:
            return
        if self._get_nb_path(record.doc_id).exists():
            self._get_nb_path(record.doc_id).unlink()
        table.remove(Query().uri == uri)
