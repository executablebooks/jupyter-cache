from contextlib import contextmanager
import copy
import io
from pathlib import Path
import hashlib
import shutil
from typing import Callable, Iterable, List, Optional, Tuple, Union

import nbformat as nbf

from jupyter_cache.base import (  # noqa: F401
    JupyterCacheAbstract,
    NbBundleIn,
    NbBundleOut,
    CachingError,
    RetrievalError,
    NbValidityError,
    NB_VERSION,
    NbArtifactsAbstract,
)
from jupyter_cache.utils import to_relative_paths
from .db import create_db, NbCacheRecord, NbStageRecord, Setting

CACHE_LIMIT_KEY = "cache_limit"
DEFAULT_CACHE_LIMIT = 1000


class NbArtifacts(NbArtifactsAbstract):
    """Container for artefacts of a notebook execution."""

    def __init__(self, paths: List[str], in_folder, check_existence=True):
        """Initiate NbArtifacts

        :param paths: list of paths
        :param check_existence: check the paths exist
        :param in_folder: The folder that all paths should be in (or subfolder).
        :raises IOError: if check_existence and file does not exist
        """
        self.paths = [Path(p).absolute() for p in paths]
        self.in_folder = Path(in_folder).absolute()
        to_relative_paths(self.paths, self.in_folder, check_existence=check_existence)

    @property
    def relative_paths(self) -> List[Path]:
        """Return the list of paths (relative to the notebook folder)."""
        return to_relative_paths(self.paths, self.in_folder)

    def __iter__(self) -> Iterable[Tuple[Path, io.BufferedReader]]:
        """Yield the relative path and open files (in bytes mode)"""
        for path in self.paths:
            with path.open("rb") as handle:
                yield path.relative_to(self.in_folder), handle


class JupyterCacheBase(JupyterCacheAbstract):
    def __init__(self, path):
        self._path = Path(path).absolute()
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

    def __repr__(self):
        return "{0}({1})".format(self.__class__.__name__, repr(str(self._path)))

    def __getstate__(self):
        """For pickling instances, db must be removed."""
        state = self.__dict__.copy()
        state["_db"] = None
        return state

    def clear_cache(self):
        """Clear the cache completely."""
        shutil.rmtree(self.path)
        self._db = None

    def _get_notebook_path_cache(self, hashkey, raise_on_missing=False) -> Path:
        """"Retrieve a relative path in the cache to a notebook, from its hash."""
        path = self.path.joinpath(Path("executed", hashkey, "base.ipynb"))
        if not path.exists() and raise_on_missing:
            raise RetrievalError("hashkey not in cache: {}".format(hashkey))
        return path

    def _get_artifact_path_cache(self, hashkey) -> Path:
        """"Retrieve a relative path in the cache to a notebook, from its hash."""
        path = self.path.joinpath(Path("executed", hashkey, "artifacts"))
        return path

    def truncate_caches(self):
        """If the number of cached notebooks exceeds set limit, delete the oldest."""
        cache_limit = Setting.get_value(CACHE_LIMIT_KEY, self.db, DEFAULT_CACHE_LIMIT)
        # TODO you could have better control over this by e.g. tagging certain caches
        # that should not be deleted.
        pks = NbCacheRecord.records_to_delete(cache_limit, self.db)
        for pk in pks:
            self.remove_cache(pk)

    def get_cache_limit(self):
        return Setting.get_value(CACHE_LIMIT_KEY, self.db, DEFAULT_CACHE_LIMIT)

    def change_cache_limit(self, size: int):
        assert isinstance(size, int) and size > 0
        Setting.set_value(CACHE_LIMIT_KEY, size, self.db)

    def create_hashed_notebook(
        self,
        nb: nbf.NotebookNode,
        nb_metadata: Optional[Iterable[str]] = ("kernelspec",),
        cell_metadata: Optional[Iterable[str]] = None,
    ) -> Tuple[nbf.NotebookNode, str]:
        """Convert a notebook to a standard format and hash.

        Note: we always hash notebooks as version 4.4,
        to allow for matching notebooks of different versions

        :param nb_metadata: The notebook metadata keys to hash (if None, use all)
        :param cell_metadata: The cell metadata keys to hash (if None, use all)

        :return: (notebook, hash)
        """
        # copy the notebook
        nb = copy.deepcopy(nb)
        # update the notebook to consistent version 4.4
        nb = nbf.convert(nb, to_version=NB_VERSION)
        if nb.nbformat_minor > 5:
            raise CachingError("notebook version greater than 4.5 not yet supported")
        # remove non-code cells
        nb.cells = [cell for cell in nb.cells if cell.cell_type == "code"]
        # create notebook for hashing, with selected metadata
        hash_nb = nbf.from_dict(
            {
                "nbformat": nb.nbformat,
                "nbformat_minor": 4,  # v4.5 include cell ids, which we do not cache
                "metadata": {
                    k: v
                    for k, v in nb.metadata.items()
                    if nb_metadata is None or (k in nb_metadata)
                },
                "cells": [
                    {
                        "cell_type": cell.cell_type,
                        "source": cell.source,
                        "metadata": {
                            k: v
                            for k, v in cell.metadata.items()
                            if cell_metadata is None or (k in cell_metadata)
                        },
                        "execution_count": None,
                        "outputs": [],
                    }
                    for cell in nb.cells
                    if cell.cell_type == "code"
                ],
            }
        )

        # hash notebook
        string = nbf.writes(hash_nb, nbf.NO_CONVERT)
        hash_string = hashlib.md5(string.encode()).hexdigest()

        return (nb, hash_string)

    def _validate_nb_bundle(self, nb_bundle: NbBundleIn):
        """Validate that a notebook bundle should be cached.

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

    def cache_notebook_bundle(
        self,
        bundle: NbBundleIn,
        check_validity: bool = True,
        overwrite: bool = False,
        description="",
    ) -> NbCacheRecord:
        """Cache an executed notebook."""
        # TODO it would be ideal to have some 'rollback' mechanism on exception

        if check_validity:
            self._validate_nb_bundle(bundle)

        hashed_nb, hashkey = self.create_hashed_notebook(bundle.nb)

        path = self._get_notebook_path_cache(hashkey)
        if path.exists():
            if not overwrite:
                raise CachingError(
                    "Notebook already exists in cache and overwrite=False."
                )
            shutil.rmtree(path.parent)
            record = NbCacheRecord.record_from_hashkey(hashkey, self.db)
            # TODO record should be changed rather than deleted?
            NbCacheRecord.remove_records([record.pk], self.db)

        record = NbCacheRecord.create_record(
            uri=bundle.uri,
            hashkey=hashkey,
            db=self.db,
            data=bundle.data,
            description=description,
        )
        path.parent.mkdir(parents=True)
        path.write_text(nbf.writes(hashed_nb, nbf.NO_CONVERT), encoding="utf8")

        # write artifacts
        artifact_folder = self._get_artifact_path_cache(hashkey)
        if artifact_folder.exists():
            shutil.rmtree(artifact_folder)
        for rel_path, handle in bundle.artifacts or []:
            write_path = artifact_folder.joinpath(rel_path)
            write_path.parent.mkdir(parents=True, exist_ok=True)
            write_path.write_bytes(handle.read())

        self.truncate_caches()

        return record

    def cache_notebook_file(
        self,
        path: str,
        uri: Optional[str] = None,
        artifacts: List[str] = (),
        data: Optional[dict] = None,
        check_validity: bool = True,
        overwrite: bool = False,
    ) -> NbCacheRecord:
        """Cache an executed notebook, returning its primary key.

        Note: non-code source text (e.g. markdown) is not stored in the cache.

        :param path: path to the notebook
        :param uri: alternative URI to store in the cache record (defaults to path)
        :param artifacts: list of paths to outputs of the executed notebook.
            Artifacts must be in the same folder as the notebook (or a sub-folder)
        :param data: additional, JSONable, data to store in the cache record
        :param check_validity: check that the notebook has been executed correctly,
            by asserting `execution_count`s are consecutive and start at 1.
        :param overwrite: Allow overwrite of cached notebooks with matching hash
        :return: The primary key of the cache record
        """
        notebook = nbf.read(str(path), nbf.NO_CONVERT)
        return self.cache_notebook_bundle(
            NbBundleIn(
                notebook,
                uri or str(path),
                artifacts=NbArtifacts(artifacts, in_folder=Path(path).parent),
                data=data or {},
            ),
            check_validity=check_validity,
            overwrite=overwrite,
        )

    def list_cache_records(self) -> List[NbCacheRecord]:
        return NbCacheRecord.records_all(self.db)

    def get_cache_record(self, pk: int) -> NbCacheRecord:
        return NbCacheRecord.record_from_pk(pk, self.db)

    def get_cache_bundle(self, pk: int) -> NbBundleOut:
        record = NbCacheRecord.record_from_pk(pk, self.db)
        NbCacheRecord.touch(pk, self.db)
        path = self._get_notebook_path_cache(record.hashkey)
        artifact_folder = self._get_artifact_path_cache(record.hashkey)
        if not path.exists():
            raise KeyError(
                "Notebook file does not exist for cache record PK: {}".format(pk)
            )

        return NbBundleOut(
            nbf.reads(path.read_text(encoding="utf8"), nbf.NO_CONVERT),
            record=record,
            artifacts=NbArtifacts(
                [p for p in artifact_folder.glob("**/*") if p.is_file()],
                in_folder=artifact_folder,
            ),
        )

    @contextmanager
    def cache_artefacts_temppath(self, pk: int) -> Path:
        """Context manager to provide a temporary folder path to the notebook artifacts.

        Note this path is only guaranteed to exist within the scope of the context,
        and should only be used for read/copy operations::

            with cache.cache_artefacts_temppath(1) as path:
                shutil.copytree(path, destination)
        """
        record = NbCacheRecord.record_from_pk(pk, self.db)
        yield self._get_artifact_path_cache(record.hashkey)

    def remove_cache(self, pk: int):
        record = NbCacheRecord.record_from_pk(pk, self.db)
        path = self._get_notebook_path_cache(record.hashkey)
        if not path.exists():
            raise KeyError(
                "Notebook file does not exist for cache record PK: {}".format(pk)
            )
        shutil.rmtree(path.parent)
        NbCacheRecord.remove_records([pk], self.db)

    def match_cache_notebook(self, nb: nbf.NotebookNode) -> NbCacheRecord:
        """Match to an executed notebook, returning its primary key.

        :raises KeyError: if no match is found
        """
        _, hashkey = self.create_hashed_notebook(nb)
        cache_record = NbCacheRecord.record_from_hashkey(hashkey, self.db)
        return cache_record

    def merge_match_into_notebook(
        self,
        nb: nbf.NotebookNode,
        nb_meta: Optional[Iterable[str]] = ("kernelspec", "language_info", "widgets"),
        cell_meta: Optional[Iterable[str]] = None,
    ) -> Tuple[int, nbf.NotebookNode]:
        """Match to an executed notebook and return a merged version

        :param nb: The input notebook
        :param nb_meta: metadata keys to merge from the cached notebook (all if None)
        :param cell_meta: cell metadata keys to merge from cached notebook (all if None)
        :raises KeyError: if no match is found
        :return: pk, input notebook with cached code cells and metadata merged.

        """
        pk = self.match_cache_notebook(nb).pk
        cache_nb = self.get_cache_bundle(pk).nb
        nb = nbf.convert(copy.deepcopy(nb), NB_VERSION)
        if nb_meta is None:
            nb.metadata = cache_nb.metadata
        else:
            for key in nb_meta:
                if key in cache_nb.metadata:
                    nb.metadata[key] = cache_nb.metadata[key]
        for idx in range(len(nb.cells)):
            if nb.cells[idx].cell_type == "code":
                cache_cell = cache_nb.cells.pop(0)
                in_cell = nb.cells[idx]
                if cell_meta is not None:
                    # update the input metadata with select cached notebook metadata
                    # then add the input metadata to the cached cell
                    in_cell.metadata.update(
                        {k: v for k, v in cache_cell.metadata.items() if k in cell_meta}
                    )
                    cache_cell.metadata = in_cell.metadata
                if nb.nbformat_minor >= 5:
                    cache_cell.id = in_cell.id
                else:
                    cache_cell.pop("id", None)
                nb.cells[idx] = cache_cell
        return pk, nb

    def diff_nbnode_with_cache(
        self, pk: int, nb: nbf.NotebookNode, uri: str = "", as_str=False, **kwargs
    ):
        """Return a diff of a notebook to a cached one.

        Note: this will not diff markdown content, since it is not stored in the cache.
        """
        import nbdime
        from nbdime.prettyprint import pretty_print_diff, PrettyPrintConfig

        cached_nb = self.get_cache_bundle(pk).nb
        nb, _ = self.create_hashed_notebook(nb)

        diff = nbdime.diff_notebooks(cached_nb, nb)
        if not as_str:
            return diff
        stream = io.StringIO()
        stream.writelines(["nbdiff\n", f"--- cached pk={pk}\n", f"+++ other: {uri}\n"])
        pretty_print_diff(
            cached_nb, diff, "nb", PrettyPrintConfig(out=stream, **kwargs)
        )
        return stream.getvalue()

    def stage_notebook_file(self, path: str, assets=()) -> NbStageRecord:
        """Stage a single notebook for execution.

        :param uri: The path to the file
        :param assets: The path of files required by the notebook to run.
            These must be within the same folder as the notebook.
        """
        return NbStageRecord.create_record(
            str(Path(path).absolute()), self.db, raise_on_exists=False, assets=assets
        )
        # TODO physically copy to cache?
        # TODO assets

    def list_staged_records(self) -> List[NbStageRecord]:
        return NbStageRecord.records_all(self.db)

    def get_staged_record(self, uri_or_pk: Union[int, str]) -> NbStageRecord:
        if isinstance(uri_or_pk, int):
            record = NbStageRecord.record_from_pk(uri_or_pk, self.db)
        else:
            record = NbStageRecord.record_from_uri(uri_or_pk, self.db)
        return record

    def discard_staged_notebook(self, uri_or_pk: Union[int, str]):
        """Discard a staged notebook."""
        if isinstance(uri_or_pk, int):
            NbStageRecord.remove_pks([uri_or_pk], self.db)
        else:
            NbStageRecord.remove_uris([uri_or_pk], self.db)

    # TODO add discard all/multiple staged records method

    def get_staged_notebook(
        self, uri_or_pk: Union[int, str], converter: Optional[Callable] = None
    ) -> NbBundleIn:
        """Return a single staged notebook."""
        if isinstance(uri_or_pk, int):
            uri_or_pk = NbStageRecord.record_from_pk(uri_or_pk, self.db).uri
        if not Path(uri_or_pk).exists():
            raise IOError(
                "The URI of the staged record no longer exists: {}".format(uri_or_pk)
            )
        if converter is None:
            notebook = nbf.read(uri_or_pk, nbf.NO_CONVERT)
        else:
            notebook = converter(uri_or_pk)
        return NbBundleIn(notebook, uri_or_pk)

    def get_cache_record_of_staged(
        self, uri_or_pk: Union[int, str], converter: Optional[Callable] = None
    ) -> Optional[NbCacheRecord]:
        if isinstance(uri_or_pk, int):
            record = NbStageRecord.record_from_pk(uri_or_pk, self.db)
        else:
            record = NbStageRecord.record_from_uri(uri_or_pk, self.db)
        nb = self.get_staged_notebook(record.uri, converter=converter).nb
        _, hashkey = self.create_hashed_notebook(nb)
        try:
            return NbCacheRecord.record_from_hashkey(hashkey, self.db)
        except KeyError:
            return None

    def list_staged_unexecuted(
        self, converter: Optional[Callable] = None
    ) -> List[NbStageRecord]:
        """List staged notebooks, whose hash is not present in the cached notebooks."""
        records = []
        for record in self.list_staged_records():
            nb = self.get_staged_notebook(record.uri, converter).nb
            _, hashkey = self.create_hashed_notebook(nb)
            try:
                NbCacheRecord.record_from_hashkey(hashkey, self.db)
            except KeyError:
                records.append(record)
        return records

    # removed until defined use case
    # def get_cache_codecell(self, pk: int, index: int) -> nbf.NotebookNode:
    #     """Return a code cell from a cached notebook.

    #     NOTE: the index **only** refers to the list of code cells, e.g.
    #     `[codecell_0, textcell_1, codecell_2]`
    #     would map {0: codecell_0, 1: codecell_2}
    #     """
    #     nb_bundle = self.get_cache_bundle(pk)
    #     _code_index = 0
    #     for cell in nb_bundle.nb.cells:
    #         if cell.cell_type != "code":
    #             continue
    #         if _code_index == index:
    #             return cell
    #         _code_index += 1
    #     raise RetrievalError(f"Notebook contains less than {index+1} code cell(s)")
