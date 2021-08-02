"""Module for handling different functions to read "notebook-like" files."""
import threading
from typing import Callable, Set

import nbformat as nbf

from .entry_points import ENTRY_POINT_GROUP_READER, get_entry_point, list_group_names

# a thread safe cache for notebook read functions
# we include this in addition to entry points, since myst_nb needs to add them dynamically
_THREAD_CACHE = threading.local()
_THREAD_CACHE.readers = {}
_READERS = _THREAD_CACHE.readers


def nbf_reader(uri: str) -> nbf.NotebookNode:
    """Standard notebook reader."""
    return nbf.read(uri, nbf.NO_CONVERT)


def jupytext_reader(uri: str) -> nbf.NotebookNode:
    """Jupytext notebook reader."""
    try:
        import jupytext
    except ImportError:
        raise ImportError("jupytext must be installed to use this reader")
    return jupytext.read(uri)


def add_reader(
    key: str,
    reader: Callable[[str], nbf.NotebookNode],
    override: bool = False,
) -> None:
    """Add a reader function to the cache.

    :param extension: The key to store the reader under.
    :param reader: A function that takes a path as input and returns a notebook node.
    :param override: If True, override an existing reader.

    """
    if not override and (
        key in _READERS or get_entry_point(ENTRY_POINT_GROUP_READER, key)
    ):
        raise ValueError(f"Reader '{key}' already exists")

    _READERS[key] = reader


def list_readers() -> Set[str]:
    """List all available readers."""
    return set(list(_READERS) + list(list_group_names(ENTRY_POINT_GROUP_READER)))


def get_reader(key: str) -> Callable[[str], nbf.NotebookNode]:
    """Returns a function to read a file URI and return a notebook."""
    if key in _READERS:
        return _READERS[key]
    reader = get_entry_point(ENTRY_POINT_GROUP_READER, key)
    if reader is not None:
        return reader.load()
    raise ValueError(f"No reader found for '{key}'")
