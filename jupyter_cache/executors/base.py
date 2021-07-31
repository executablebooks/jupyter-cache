import logging
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

import attr

# TODO use importlib.metadata
import pkg_resources

from jupyter_cache.base import JupyterCacheAbstract

ENTRY_POINT_GROUP = "jupyter_executors"

base_logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    pass


@attr.s(slots=True)
class ExecutorRunResult:
    """A container for the execution result."""

    # URIs of notebooks which where successfully executed
    succeeded: List[str] = attr.ib(factory=list)
    # URIs of notebooks which excepted during execution
    excepted: List[str] = attr.ib(factory=list)
    # URIs of notebooks which errored before execution
    errored: List[str] = attr.ib(factory=list)

    def all(self) -> List[str]:
        """Return all notebooks."""
        return self.succeeded + self.excepted + self.errored

    def as_json(self) -> Dict[str, Any]:
        """Return the result as a JSON serializable dict."""
        return {
            "succeeded": self.succeeded,
            "excepted": self.excepted,
            "errored": self.errored,
        }


class JupyterExecutorAbstract(ABC):
    """An abstract class for executing notebooks in a cache."""

    def __init__(self, cache: JupyterCacheAbstract, logger=None):
        self._cache = cache
        self._logger = logger or logging.getLogger(__name__)

    def __repr__(self):
        return "{0}(cache={1})".format(self.__class__.__name__, self._cache)

    @property
    def cache(self):
        return self._cache

    @property
    def logger(self):
        return self._logger

    @abstractmethod
    def run_and_cache(
        self,
        *,
        filter_uris: Optional[List[str]] = None,
        filter_pks: Optional[List[int]] = None,
        converter: Optional[Callable] = None,
        timeout: Optional[int] = 30,
        allow_errors: bool = False,
        **kwargs: Any
    ) -> ExecutorRunResult:
        """Run execution, cache successfully executed notebooks and return their URIs

        Parameters
        ----------
        filter_uris: list
            If specified filter the staged notebooks to execute by these URIs
        filter_pks: list
            If specified filter the staged notebooks to execute by these PKs
        converter:
            An optional converter for staged notebooks,
            which takes the URI and returns a notebook node
        timeout: int
            Maximum time in seconds to wait for a single cell to run for
        allow_errors: bool
            Whether to halt execution on the first cell exception
            (provided the cell is not tagged as an expected exception)
        """


def list_executors():
    return list(pkg_resources.iter_entry_points(ENTRY_POINT_GROUP))


def load_executor(
    entry_point: str, cache: JupyterCacheAbstract, logger=None
) -> JupyterExecutorAbstract:
    """Retrieve an initialised JupyterExecutor from an entry point."""
    entry_points = list(pkg_resources.iter_entry_points(ENTRY_POINT_GROUP, entry_point))
    if len(entry_points) == 0:
        raise ImportError(
            "Entry point not found: {}.{}".format(ENTRY_POINT_GROUP, entry_point)
        )
    if len(entry_points) != 1:
        raise ImportError(
            "Multiple entry points found: {}.{}".format(ENTRY_POINT_GROUP, entry_point)
        )
    execute_cls = entry_points[0].load()
    return execute_cls(cache=cache, logger=logger)
