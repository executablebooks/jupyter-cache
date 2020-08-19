from pathlib import Path
import shutil
import tempfile

# from jupyter_client.kernelspec import get_kernel_spec, NoSuchKernel

from jupyter_cache.executors.base import JupyterExecutorAbstract
from jupyter_cache.executors.utils import single_nb_execution
from jupyter_cache.cache.main import NbBundleIn, NbArtifacts
from jupyter_cache.cache.db import NbStageRecord
from jupyter_cache.utils import to_relative_paths


class ExecutionError(Exception):
    """An exception to signify a error during execution of a specific URI."""

    def __init__(self, message, uri, exc):
        self.uri = uri
        self.exc = exc
        return super().__init__(message)


class JupyterExecutorBasic(JupyterExecutorAbstract):
    """A basic implementation of an executor.

    The execution is split into two methods: `run` and `execute`.
    In this way access to the cache can be synchronous, but the execution can be
    multi/async processed. Takes timeout parameter in seconds for execution
    """

    def run_and_cache(
        self,
        filter_uris=None,
        filter_pks=None,
        converter=None,
        timeout=30,
        allow_errors=False,
        run_in_temp=True,
    ):
        """This function interfaces with the cache, deferring execution to `execute`."""
        # Get the notebook tha require re-execution
        stage_records = self.cache.list_staged_unexecuted(converter=converter)
        if filter_uris is not None:
            stage_records = [r for r in stage_records if r.uri in filter_uris]
        if filter_pks is not None:
            stage_records = [r for r in stage_records if r.pk in filter_pks]

        # remove any tracebacks from previous executions
        NbStageRecord.remove_tracebacks([r.pk for r in stage_records], self.cache.db)

        # setup an dictionary to categorise all executed notebook uris:
        # excepted are where the actual notebook execution raised an exception;
        # errored is where any other exception was raised
        result = {"succeeded": [], "excepted": [], "errored": []}
        # we pass an iterator to the execute method,
        # so that we don't have to read all notebooks before execution

        def _iterator():
            for stage_record in stage_records:
                try:
                    nb_bundle = self.cache.get_staged_notebook(
                        stage_record.pk, converter
                    )
                except Exception:
                    self.logger.error(
                        "Failed Retrieving: {}".format(stage_record.uri), exc_info=True
                    )
                    result["errored"].append(stage_record.uri)
                else:
                    yield stage_record, nb_bundle

        # The execute method yields notebook bundles, or ExecutionError
        for bundle_or_exc in self.execute(
            _iterator(), int(timeout), allow_errors, run_in_temp
        ):
            if isinstance(bundle_or_exc, ExecutionError):
                self.logger.error(bundle_or_exc.uri, exc_info=bundle_or_exc.exc)
                result["errored"].append(bundle_or_exc.uri)
                continue
            elif bundle_or_exc.traceback is not None:
                # The notebook raised an exception during execution
                # TODO store excepted bundles
                result["excepted"].append(bundle_or_exc.uri)
                NbStageRecord.set_traceback(
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
                result["errored"].append(bundle_or_exc.uri)
            else:
                result["succeeded"].append(bundle_or_exc.uri)

        # TODO it would also be ideal to tag all notebooks
        # that were executed at the same time (just part of `data` or separate column?).
        # TODO maybe the status of success/failure could be explicitly stored on
        # the stage record (cache_status=Enum('OK', 'FAILED', 'MISSING'))
        # although now traceback is so this is an implicit sign of failure,
        # TODO failed notebooks could be stored in the cache, which would be
        # accessed by stage pk (and would be deleted when removing the stage record)
        # see: https://python.quantecon.org/status.html

        return result

    def execute(self, input_iterator, timeout=30, allow_errors=False, in_temp=True):
        """This function is isolated from the cache, and is responsible for execution.

        The method is only supplied with the staged record and input notebook bundle,
        it then yield results for caching
        """
        for stage_record, nb_bundle in input_iterator:
            try:
                uri = nb_bundle.uri
                self.logger.info("Executing: {}".format(uri))

                if in_temp:
                    with tempfile.TemporaryDirectory() as tmpdirname:

                        try:
                            asset_files = _copy_assets(stage_record, tmpdirname)
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
                else:
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

    def execute_single(self, nb_bundle, uri, cwd, timeout, allow_errors, asset_files):
        result = single_nb_execution(
            nb_bundle.nb, cwd=cwd, timeout=timeout, allow_errors=allow_errors,
        )
        if result.err:
            self.logger.error("Execution Failed: {}".format(uri))
            return _create_bundle(
                nb_bundle, cwd, asset_files, result.time, result.exc_string,
            )

        self.logger.info("Execution Succeeded: {}".format(uri))
        return _create_bundle(nb_bundle, cwd, asset_files, result.time, None)


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
