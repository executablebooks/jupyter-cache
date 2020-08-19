import attr

from typing import Optional, Union
import traceback

from nbformat import NotebookNode
from nbclient import execute as executenb
from nbclient.client import CellExecutionError, CellTimeoutError

from jupyter_cache.utils import Timer


@attr.s()
class ExecutionResult:
    nb: NotebookNode = attr.ib()
    time: float = attr.ib()
    err: Optional[Union[CellExecutionError, CellTimeoutError]] = attr.ib(default=None)
    exc_string: Optional[str] = attr.ib(default=None)


def single_nb_execution(
    nb: NotebookNode,
    cwd: Optional[str],
    timeout: Optional[int],
    allow_errors: bool,
    meta_override: bool = True,
) -> ExecutionResult:
    """Execute notebook in place.

    :param cwd: If supplied, the kernel will run in this directory.
    :param timeout: The time to wait (in seconds) for output from executions.
                If a cell execution takes longer, a ``TimeoutError`` is raised.
    :param allow_errors: If ``False`` when a cell raises an error the
                execution is stopped and a ``CellExecutionError`` is raised.
    :param meta_override: If ``True`` then timeout and allow_errors may be overridden
                by equivalent keys in nb.metadata.execution

    :returns: The execution time in seconds
    """
    if meta_override and "execution" in nb.metadata:
        if "timeout" in nb.metadata.execution:
            timeout = nb.metadata.execution.timeout
        if "allow_errors" in nb.metadata.execution:
            allow_errors = nb.metadata.execution.allow_errors

    error = exc_string = None
    # TODO nbclient with record_timing=True will add execution data to each cell
    timer = Timer()
    with timer:
        try:
            executenb(
                nb,
                cwd=cwd,
                timeout=timeout,
                allow_errors=allow_errors,
                record_timing=False,
            )
        except (CellExecutionError, CellTimeoutError) as err:
            error = err
            exc_string = "".join(traceback.format_exc())

    return ExecutionResult(nb, timer.last_split, error, exc_string)
