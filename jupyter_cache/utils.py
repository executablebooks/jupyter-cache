from pathlib import Path
import time
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
        self._split_time = 0

    @property
    def last_split(self):
        return self._split_time

    def reset(self):
        """Reset timer."""
        self._last_time = time.perf_counter()
        self._split_time = 0

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
