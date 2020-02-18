from contextlib import contextmanager
import pathlib
from sqlite3 import Connection as SQLite3Connection
from typing import Iterator, Optional, Set

import sqlalchemy as sqla
from sqlalchemy.orm import sessionmaker, Session

import nbformat as nbf

from jupyter_cache.base import JupyterCacheAbstract, CachingError, RetrievalError
from .orm import (  # noqa: F401
    OrmBase,
    OrmCellExecution,
    OrmCodeCell,
    OrmDocument,
    OrmKernel,
    OrmKernelInfo,
    OrmOutput,
    OrmOutputDisplay,
    OrmOutputError,
    OrmOutputExecute,
    OrmOutputStream,
    OrmMimeBundle,
)


@sqla.event.listens_for(sqla.engine.Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce foreign key constraints, when using sqlite backend (off by default)"""
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


class JupyterCacheSql(JupyterCacheAbstract):
    """An SQL based database cache for code kernels, cells, outputs, etc."""

    def __init__(self, db_folder_path: str, db_file_name: str = "jupyter.db", **kwargs):
        self._db_path = (pathlib.Path(db_folder_path) / db_file_name).absolute()
        self._engine = sqla.create_engine(
            "sqlite:///{}".format(self._db_path), **kwargs
        )
        OrmBase.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)

    @property
    def declarative(self) -> sqla.ext.declarative.DeclarativeMeta:
        return OrmBase

    def __getstate__(self):
        """For pickling instance."""
        state = self.__dict__.copy()
        state["_engine"] = None
        state["_session_factory"] = None
        return state

    def __setstate__(self, newstate):
        """For unpickling instance."""
        newstate["_engine"] = sqla.create_engine(
            "sqlite:///{}".format(newstate["_db_path"])
        )
        newstate["_session_factory"] = sessionmaker(bind=newstate["_engine"])
        self.__dict__.update(newstate)

    @contextmanager
    def context_session(self, *, session=None, final_commit=True) -> Iterator[Session]:
        """Provide a transactional scope around a series of operations."""
        if session is None:
            session = self._session_factory()
            close_on_exit = True
        else:
            close_on_exit = False
        try:
            yield session
            if final_commit:
                session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            if close_on_exit:
                session.close()

    def to_dict(self, *, drop_tables=(), drop_columns=()) -> dict:
        """Convert all database tables to json (for testing purposes)."""
        result = {}
        with self.context_session() as session:  # type: Session
            for name, entity in OrmBase.metadata.tables.items():
                if name in drop_tables:
                    continue
                drop_cols = (
                    drop_columns.get(name, ())
                    if isinstance(drop_columns, dict)
                    else drop_columns
                )
                result[name] = [
                    {k: v for k, v in r._asdict().items() if k not in drop_cols}
                    for r in session.query(entity)
                ]
        return result

    def add_notebook_node(
        self,
        node: nbf.NotebookNode,
        uri: str,
        overwrite=False,
        *,
        session: Optional[Session] = None,
    ):
        """Add a single notebook to the cache."""
        with self.context_session(
            session=session, final_commit=True
        ) as session:  # type: Session
            doc = session.query(OrmDocument).filter_by(uri=uri).one_or_none()
            if doc and overwrite:
                session.delete(doc)
            elif doc:
                raise CachingError(f"document already exists: {uri}")
            doc = OrmDocument(uri=uri)
            session.add(doc)
            session.commit()
            doc.kernels = [OrmKernel.from_nbformat(nb=node, doc_pk=doc.pk, doc_order=0)]
            session.add(doc)

    def get_notebook(
        self, uri: str, with_outputs=True, *, session: Optional[Session] = None
    ) -> nbf.NotebookNode:
        """Get a single notebook from the cache.

        If `with_outputs` is False, return with all outputs removed.
        """
        with self.context_session(
            session=session, final_commit=False
        ) as session:  # type: Session
            doc = session.query(OrmDocument).filter_by(uri=uri).one_or_none()
            if doc is None or not doc.kernels:
                raise RetrievalError(uri)
            if len(doc.kernels) > 1:
                raise RetrievalError(f"document has more than one kernel: {uri}")
            kernel = doc.kernels[0]
            return kernel.to_nbformat(with_outputs=with_outputs)

    def remove_notebook(self, uri: str, *, session: Optional[Session] = None):
        """Remove a document and its associated kernels and code cells."""
        with self.context_session(
            session=session, final_commit=True
        ) as session:  # type: Session
            doc = session.query(OrmDocument).filter_by(uri=uri).one_or_none()
            if doc is None:
                return
            session.delete(doc)

    def list_notebooks(self, *, session: Optional[Session] = None) -> Set[str]:
        """list the notebook uri's in the cache."""
        with self.context_session(
            session=session, final_commit=False
        ) as session:  # type: Session
            uris = session.query(OrmDocument.uri).all()
        return {u for u, in uris}

    def get_codecell(
        self, uri: str, index: int, *, session: Optional[Session] = None
    ) -> nbf.NotebookNode:
        """Return the code cell from a particular notebook.

        NOTE: the index **only** refers to the list of code cells, e.g.
        `[codecell_0, textcell_1, codecell_2]` would map {0: codecell_0, 1: codecell_2}
        """
        with self.context_session(
            session=session, final_commit=False
        ) as session:  # type: Session
            doc: OrmDocument = session.query(OrmDocument).filter_by(
                uri=uri
            ).one_or_none()
            if doc is None:
                raise RetrievalError(f"uri: {uri}")
            if len(doc.codecells) < (index + 1):
                raise RetrievalError(
                    f"notebook contains less than {index+1} code cell(s)"
                )
            cell = doc.codecells[index]
            nb_cell = cell.to_nbformat(with_outputs=True)
        return nb_cell
