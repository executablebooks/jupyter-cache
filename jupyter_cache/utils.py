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
