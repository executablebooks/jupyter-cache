import shutil
import tempfile
from pathlib import Path
from typing import Optional

from jupyter_cache.cache.db import NbProjectRecord
from jupyter_cache.cache.main import NbArtifacts, NbBundleIn
from jupyter_cache.executors.base import ExecutorRunResult, JupyterExecutorAbstract
from jupyter_cache.executors.utils import single_nb_execution
from jupyter_cache.utils import to_relative_paths

# from jupyter_client.kernelspec import get_kernel_spec, NoSuchKernel


class ExecutionError(Exception):
    """An exception to signify a error during execution of a specific URI."""

    def __init__(self, message, uri, exc):
        self.uri = uri
        self.exc = exc
        return super().__init__(message)


class JupyterExecutorLocalSerial(JupyterExecutorAbstract):
    """A basic implementation of an executor; executing locally in serial.

    The execution is split into two methods: `run` and `execute`.
    In this way access to the cache can be synchronous, but the execution can be
    multi/async processed. Takes timeout parameter in seconds for execution
    """

    def run_and_cache(
        self,
        *,
        filter_uris=None,
        filter_pks=None,
        timeout=30,
        allow_errors=False,
    ) -> ExecutorRunResult:
        """This function interfaces with the cache, deferring execution to `execute`."""
        # Get the notebook tha require re-execution
        execute_records = self.cache.list_unexecuted()
        if filter_uris is not None:
            execute_records = [r for r in execute_records if r.uri in filter_uris]
        if filter_pks is not None:
            execute_records = [r for r in execute_records if r.pk in filter_pks]

        # remove any tracebacks from previous executions
        NbProjectRecord.remove_tracebacks(
            [r.pk for r in execute_records], self.cache.db
        )

        # setup an dictionary to categorise all executed notebook uris:
        # excepted are where the actual notebook execution raised an exception;
        # errored is where any other exception was raised
        result = ExecutorRunResult()
        # we pass an iterator to the execute method,
        # so that we don't have to read all notebooks before execution

        def _iterator():
            for execute_record in execute_records:
                try:
                    nb_bundle = self.cache.get_project_notebook(execute_record.pk)
                except Exception:
                    self.logger.error(
                        "Failed Retrieving: {}".format(execute_record.uri),
                        exc_info=True,
                    )
                    result.errored.append(execute_record.uri)
                else:
                    yield execute_record, nb_bundle

        # The execute method yields notebook bundles, or ExecutionError
        for bundle_or_exc in self.execute(
            _iterator(),
            int(timeout),
            allow_errors,
        ):
            if isinstance(bundle_or_exc, ExecutionError):
                self.logger.error(bundle_or_exc.uri, exc_info=bundle_or_exc.exc)
                result.errored.append(bundle_or_exc.uri)
                continue
            elif bundle_or_exc.traceback is not None:
                # The notebook raised an exception during execution
                # TODO store excepted bundles
                result.excepted.append(bundle_or_exc.uri)
                NbProjectRecord.set_traceback(
                    bundle_or_exc.uri, bundle_or_exc.traceback, self.cache.db
                )
                continue
            try:
                # cache a successfully executed notebook
                self.cache.cache_notebook_bundle(
                    bundle_or_exc, check_validity=False, overwrite=True
                )
            except Exception:
                self.logger.error(
                    "Failed Caching: {}".format(bundle_or_exc.uri), exc_info=True
                )
                result.errored.append(bundle_or_exc.uri)
            else:
                result.succeeded.append(bundle_or_exc.uri)

        # TODO it would also be ideal to tag all notebooks
        # that were executed at the same time (just part of `data` or separate column?).
        # TODO maybe the status of success/failure could be explicitly stored on
        # the project record (cache_status=Enum('OK', 'FAILED', 'MISSING'))
        # although now traceback is so this is an implicit sign of failure,
        # TODO failed notebooks could be stored in the cache, which would be
        # accessed by the project pk (and would be deleted when removing the project record)
        # see: https://python.quantecon.org/status.html

        return result

    def execute_single(
        self,
        nb_bundle,
        uri: str,
        cwd: Optional[str],
        timeout: Optional[int],
        allow_errors: bool,
        asset_files,
    ):
        result = single_nb_execution(
            nb_bundle.nb,
            cwd=cwd,
            timeout=timeout,
            allow_errors=allow_errors,
        )
        if result.err:
            self.logger.error("Execution Failed: {}".format(uri))
            return _create_bundle(
                nb_bundle,
                cwd,
                asset_files,
                result.time,
                result.exc_string,
            )

        self.logger.info("Execution Succeeded: {}".format(uri))
        return _create_bundle(nb_bundle, cwd, asset_files, result.time, None)

    def execute(self, input_iterator, timeout=30, allow_errors=False):
        """This function is isolated from the cache, and is responsible for execution.

        The method is only supplied with the project record and input notebook bundle,
        it then yields results for caching
        """
        for _, nb_bundle in input_iterator:
            try:
                uri = nb_bundle.uri
                self.logger.info("Executing: {}".format(uri))

                yield self.execute_single(
                    nb_bundle,
                    uri,
                    str(Path(uri).parent),
                    timeout,
                    allow_errors,
                    None,
                )

            except Exception as err:
                yield ExecutionError("Unexpected Error", uri, err)


class JupyterExecutorTempSerial(JupyterExecutorLocalSerial):
    """An implementation of an executor; executing in a temporary folder in serial."""

    def execute(self, input_iterator, timeout=30, allow_errors=False):
        """This function is isolated from the cache, and is responsible for execution.

        The method is only supplied with the project record and input notebook bundle,
        it then yields results for caching.
        """
        for execute_record, nb_bundle in input_iterator:
            try:
                uri = nb_bundle.uri
                self.logger.info("Executing: {}".format(uri))

                with tempfile.TemporaryDirectory() as tmpdirname:

                    try:
                        asset_files = _copy_assets(execute_record, tmpdirname)
                    except Exception as err:
                        yield ExecutionError("Assets Retrieval Error", uri, err)
                        continue

                    yield self.execute_single(
                        nb_bundle,
                        uri,
                        tmpdirname,
                        timeout,
                        allow_errors,
                        asset_files,
                    )

            except Exception as err:
                yield ExecutionError("Unexpected Error", uri, err)


def _copy_assets(record, folder):
    """Copy notebook assets to the folder the notebook will be executed in."""
    asset_files = []
    relative_paths = to_relative_paths(record.assets, Path(record.uri).parent)
    for path, rel_path in zip(record.assets, relative_paths):
        temp_file = Path(folder).joinpath(rel_path)
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, temp_file)
        asset_files.append(temp_file)
    return asset_files


def _create_bundle(nb_bundle, tmpdirname, asset_files, exec_time, exec_tb):
    """Create a cache bundle."""
    return NbBundleIn(
        nb_bundle.nb,
        nb_bundle.uri,
        # TODO retrieve assets that have changed file mtime?
        artifacts=NbArtifacts(
            [p for p in Path(tmpdirname).glob("**/*") if p not in asset_files],
            tmpdirname,
        )
        if asset_files is not None
        else None,
        data={"execution_seconds": exec_time},
        traceback=exec_tb,
    )
