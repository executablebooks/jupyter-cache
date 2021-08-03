"""Non-core imports in this module are lazily loaded, in order to improve CLI speed """

import time
from pathlib import Path
from typing import List, Union


def to_relative_paths(
    paths: List[Union[str, Path]],
    folder: Union[str, Path],
    check_existence: bool = False,
) -> List[Path]:
    """Make paths relative to a reference folder.

    :param paths: list of paths
    :param folder: The folder that all paths should be in (or subfolder).
    :param check_existence: check the paths exist
    :raises IOError: path is not relative or failed existence check

    """
    rel_paths = []
    folder = Path(folder).absolute()
    for path in paths:
        path = Path(path).absolute()
        if check_existence and not path.exists():
            raise IOError(f"Path does not exist: {path}")
        if check_existence and not path.is_file():
            raise IOError(f"Path is not a file: {path}")
        try:
            rel_path = path.relative_to(folder)
        except ValueError:
            raise IOError(f"Path '{path}' is not in folder '{folder}''")
        rel_paths.append(rel_path)
    return rel_paths


class Timer:
    """Context manager for timing runtime."""

    def __init__(self):
        self._last_time = time.perf_counter()
        self._split_time = 0.0

    @property
    def last_split(self):
        return self._split_time

    def reset(self):
        """Reset timer."""
        self._last_time = time.perf_counter()
        self._split_time = 0.0

    def split(self):
        """Record a split time."""
        self._split_time = time.perf_counter() - self._last_time

    def __enter__(self):
        """Reset timer."""
        self.reset()
        return self

    def __exit__(self, *exc_info):
        """Record a split time."""
        self.split()


def shorten_path(file_path, length):
    """Split the path into separate parts,
    select the last 'length' elements and join them again
    """
    if length is None:
        return Path(file_path)
    return Path(*Path(file_path).parts[-length:])


def tabulate_cache_records(records: list, hashkeys=False, path_length=None) -> str:
    """Tabulate cache records.

    :param records: list of ``NbCacheRecord``
    :param hashkeys: include a hashkey column
    :param path_length: truncate URI paths to x components
    """
    import tabulate

    return tabulate.tabulate(
        [
            r.format_dict(hashkey=hashkeys, path_length=path_length, show_data=False)
            for r in sorted(records, key=lambda r: r.accessed, reverse=True)
        ],
        headers="keys",
    )


def tabulate_project_records(
    records: list, path_length=None, cache=None, assets=False
) -> str:
    """Tabulate cache records.

    :param records: list of ``NbProjectRecord``
    :param path_length: truncate URI paths to x components
    :param cache: If the cache is given,
        we use it to add a column of matched cached pk (if available)
    :param assets: Show the number of assets
    """
    import tabulate

    rows = []
    for record in records:
        cache_record = None
        if cache is not None:
            cache_record = cache.get_cached_project_nb(record.uri)
        rows.append(
            record.format_dict(
                cache_record=cache_record, path_length=path_length, assets=assets
            )
        )
    return tabulate.tabulate(rows, headers="keys")
