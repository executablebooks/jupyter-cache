import copy
import io
from pathlib import Path
import hashlib
from shutil import rmtree
from typing import List

import nbdime
import nbformat as nbf
from nbdime.prettyprint import pretty_print_diff, PrettyPrintConfig

from jupyter_cache.base import (  # noqa: F401
    JupyterCacheAbstract,
    NbBundleIn,
    NbBundleOut,
    CachingError,
    RetrievalError,
    NbValidityError,
    NB_VERSION,
)

from .db import create_db, NbCommitRecord, NbStageRecord, Setting

CACHE_SIZE_KEY = "cache_size"
DEFAULT_CACHE_SIZE = 1000


class JupyterCacheBase(JupyterCacheAbstract):
    def __init__(self, path):
        self._path = Path(path)
        self._db = None

    @property
    def path(self):
        if not self._path.exists():
            self._path.mkdir(parents=True)
        return self._path

    @property
    def db(self):
        """a simple database for storing persistent global data."""
        if self._db is None:
            self._db = create_db(self.path)
        return self._db

    def __getstate__(self):
        """For pickling instances, db must be removed."""
        state = self.__dict__.copy()
        state["_db"] = None
        return state

    def clear_cache(self):
        """Clear the cache completely."""
        rmtree(self.path)
        self._db = None

    def _get_notebook_path_commit(self, hashkey, raise_on_missing=False) -> Path:
        """"Retrieve a relative path in the cache to a notebook, from its hash."""
        path = self.path.joinpath(Path("executed", hashkey, "base.ipynb"))
        if not path.exists() and raise_on_missing:
            raise RetrievalError("hashkey not in cache: {}".format(hashkey))
        return path

    def limit_cache_size(self):
        """Ensure the cache is limited to the required size,
        by deleting the oldest commits.
        """
        cache_size = Setting.get_value(CACHE_SIZE_KEY, self.db, DEFAULT_CACHE_SIZE)
        pks = NbCommitRecord.records_to_delete(cache_size, self.db)
        for pk in pks:
            self.remove_commit(pk)

    def change_cache_size(self, size: int):
        assert isinstance(size, int) and size > 0
        Setting.set_value(CACHE_SIZE_KEY, size, self.db)

    def _create_hashable_nb(
        self,
        nb: nbf.NotebookNode,
        compare_nb_meta=("kernelspec",),
        compare_cell_meta=None,
    ):
        """Create a notebook containing only content desired for hashing."""
        nb = copy.deepcopy(nb)
        nb.metadata = nbf.from_dict(
            {
                k: v
                for k, v in nb.metadata.items()
                if compare_nb_meta is None or (k in compare_nb_meta)
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
                        if compare_cell_meta is None or (k in compare_cell_meta)
                    },
                    "execution_count": None,
                    "outputs": [],
                }
            )
            diff_cells.append(diff_cell)
        nb.cells = diff_cells
        return nb

    def _hash_notebook(
        self,
        nb: nbf.NotebookNode,
        compare_nb_meta=("kernelspec", "invalidated"),
        compare_cell_meta=None,
    ):
        """Create a hashkey for a notebook bundle."""
        nb = self._create_hashable_nb(
            nb, compare_nb_meta=compare_nb_meta, compare_cell_meta=compare_cell_meta
        )
        string = nbf.writes(nb, NB_VERSION)
        return hashlib.md5(string.encode()).hexdigest()

    def _validate_nb_bundle(self, nb_bundle: NbBundleIn):
        """Validate that a notebook bundle should be committed.

        We check that the notebook has been executed correctly,
        by asserting `execution_count`s are consecutive and start at 1.
        """
        execution_count = 1
        for i, cell in enumerate(nb_bundle.nb.cells):
            if cell.cell_type != "code":
                continue
            if cell.execution_count != execution_count:
                raise NbValidityError(
                    "Expected cell {} to have execution_count {} not {}".format(
                        i, execution_count, cell.execution_count
                    ),
                    nb_bundle,
                )
            execution_count += 1
            # TODO check for output exceptions?
        # TODO assets

    def commit_notebook_bundle(
        self,
        bundle: NbBundleIn,
        check_validity: bool = True,
        overwrite: bool = False,
        description="",
    ):
        """Commit an executed notebook."""
        if check_validity:
            self._validate_nb_bundle(bundle)
        hashkey = self._hash_notebook(bundle.nb)
        path = self._get_notebook_path_commit(hashkey)
        if path.exists():
            if not overwrite:
                raise CachingError(
                    "Notebook already exists in cache and overwrite=False."
                )
            rmtree(path.parent)
            record = NbCommitRecord.record_from_hashkey(hashkey, self.db)
            # TODO record should be changed rather than deleted
            NbCommitRecord.remove_records([record.pk], self.db)

        record = NbCommitRecord.create_record(
            uri=bundle.uri, hashkey=hashkey, db=self.db, description=description
        )
        path.parent.mkdir(parents=True)
        path.write_text(nbf.writes(bundle.nb, NB_VERSION))
        self.limit_cache_size()
        return record.pk

    def list_commit_records(self) -> List[NbCommitRecord]:
        return NbCommitRecord.records_all(self.db)

    def get_commit_record(self, pk: int) -> dict:
        return NbCommitRecord.record_from_pk(pk, self.db).to_dict()

    def get_commit_bundle(self, pk: int) -> NbBundleOut:
        record = NbCommitRecord.record_from_pk(pk, self.db)
        NbCommitRecord.touch(pk, self.db)
        path = self._get_notebook_path_commit(record.hashkey)
        if not path.exists():
            raise KeyError(pk)
        # TODO optionally include assets
        # TODO cache notebook reads in memory (when retrieving from this cache,
        # should check that the cache represents the last commit)
        # this will be important when adding queries for specific cell outputs
        return NbBundleOut(
            nbf.reads(path.read_text(), NB_VERSION), commit=record.to_dict()
        )

    def get_commit_codecell(self, pk: int, index: int) -> nbf.NotebookNode:
        """Return a code cell from a committed notebook.

        NOTE: the index **only** refers to the list of code cells, e.g.
        `[codecell_0, textcell_1, codecell_2]`
        would map {0: codecell_0, 1: codecell_2}
        """
        nb_bundle = self.get_commit_bundle(pk)
        _code_index = 0
        for cell in nb_bundle.nb.cells:
            if cell.cell_type != "code":
                continue
            if _code_index == index:
                return cell
            _code_index += 1
        raise RetrievalError(f"Notebook contains less than {index+1} code cell(s)")

    def remove_commit(self, pk: int):
        record = NbCommitRecord.record_from_pk(pk, self.db)
        path = self._get_notebook_path_commit(record.hashkey)
        if not path.exists():
            raise KeyError(pk)
        rmtree(path.parent)
        NbCommitRecord.remove_records([pk], self.db)

    def match_commit_notebook(self, nb: nbf.NotebookNode):
        hashkey = self._hash_notebook(nb)
        commit_record = NbCommitRecord.record_from_hashkey(hashkey, self.db)
        return commit_record.pk

    def diff_nbnode_with_commit(
        self, pk: int, nb: nbf.NotebookNode, uri: str = "", as_str=False, **kwargs
    ):
        """Return a diff of a notebook to a committed one."""
        committed_nb = self.get_commit_bundle(pk).nb
        diff = nbdime.diff_notebooks(committed_nb, nb)
        if not as_str:
            return diff
        stream = io.StringIO()
        stream.writelines(
            ["nbdiff\n", f"--- committed pk={pk}\n", f"+++ other: {uri}\n"]
        )
        pretty_print_diff(
            committed_nb, diff, "nb", PrettyPrintConfig(out=stream, **kwargs)
        )
        return stream.getvalue()

    def stage_notebook_file(self, path: str):
        """Stage a single notebook for execution."""
        NbStageRecord.create_record(
            str(Path(path).absolute()), self.db, raise_on_exists=False
        )
        # TODO physically copy to cache?
        # TODO assets

    def discard_staged_notebook(self, uri: str):
        """Discard a staged notebook."""
        NbStageRecord.remove_uris([uri], self.db)

    def list_staged_records(self) -> List[NbStageRecord]:
        return NbStageRecord.records_all(self.db)

    def get_staged_notebook(self, uri: str) -> NbBundleIn:
        """Return a single notebook from the cache."""
        notebook = nbf.read(uri, NB_VERSION)
        return NbBundleIn(notebook, uri)

    def get_commit_record_of_staged(self, uri: str):
        record = NbStageRecord.record_from_uri(uri, self.db)
        nb = self.get_staged_notebook(record.uri).nb
        hashkey = self._hash_notebook(nb)
        try:
            return NbCommitRecord.record_from_hashkey(hashkey, self.db)
        except KeyError:
            return None

    def list_nbs_to_exec(self) -> List[dict]:
        """List staged notebooks, whose hash is not present in the cache commits."""
        records = []
        for record in self.list_staged_records():
            nb = self.get_staged_notebook(record.uri).nb
            hashkey = self._hash_notebook(nb)
            try:
                NbCommitRecord.record_from_hashkey(hashkey, self.db)
            except KeyError:
                records.append(record)
        return records
