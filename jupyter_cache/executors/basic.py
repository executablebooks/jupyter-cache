from pathlib import Path
import shutil
import tempfile
import traceback

from nbconvert.preprocessors.execute import executenb

# from jupyter_client.kernelspec import get_kernel_spec, NoSuchKernel

from jupyter_cache.executors.base import JupyterExecutorAbstract
from jupyter_cache.cache.main import NbBundleIn, NbArtifacts
from jupyter_cache.cache.db import NbStageRecord
from jupyter_cache.utils import to_relative_paths, Timer


def copy_assets(record, folder):
    asset_files = []
    relative_paths = to_relative_paths(record.assets, Path(record.uri).parent)
    for path, rel_path in zip(record.assets, relative_paths):
        temp_file = Path(folder).joinpath(rel_path)
        temp_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, temp_file)
        asset_files.append(temp_file)
    return asset_files


def create_bundle(nb_bundle, tmpdirname, asset_files, exec_time, exec_tb=None):
    return NbBundleIn(
        nb_bundle.nb,
        nb_bundle.uri,
        # TODO retrieve assets that have changed file mtime?
        artifacts=NbArtifacts(
            [p for p in Path(tmpdirname).glob("**/*") if p not in asset_files],
            tmpdirname,
        ),
        data={"execution_seconds": exec_time},
        traceback=exec_tb,
    )


class JupyterExecutorBasic(JupyterExecutorAbstract):
    """A basic implementation of an executor."""

    def run(self):
        """This function interfaces with the cache, deferring execution to _execute."""
        NbStageRecord.remove_tracebacks(self.cache.db)
        iterator = iter(
            (r, self.cache.get_staged_notebook(r.pk))
            for r in self.cache.list_nbs_to_exec()
        )
        result = {"succeeded": [], "excepted": [], "errored": []}
        for exc_bundle in self._execute(iterator):
            if exc_bundle is None:
                # TODO deal with bundles that return None
                continue
            if exc_bundle.traceback is not None:
                # TODO store excepted bundles
                result["excepted"].append(exc_bundle.uri)
                NbStageRecord.set_traceback(
                    exc_bundle.uri, exc_bundle.traceback, self.cache.db
                )
                continue
            try:
                self.cache.cache_notebook_bundle(exc_bundle, overwrite=True)
            except Exception:
                self.logger.error(
                    "Failed Caching: {}".format(exc_bundle.uri), exc_info=True
                )
                result["errored"].append(exc_bundle.uri)
            else:
                result["succeeded"].append(exc_bundle.uri)

        # TODO it would also be ideal to tag all notebooks
        # that were executed at the same time (just part of `data` or separate column?).
        # TODO maybe the status of success/failure could be stored on
        # the stage record (cache_status=Enum('OK', 'FAILED', 'MISSING'))
        # also failed notebooks could be stored in the cache, which would be
        # accessed by stage pk (and would be deleted when removing the stage record)
        # see: https://python.quantecon.org/status.html

        return result

    def _execute(self, input_iterator):
        """This function is isolated from the cache, and is responsible for execution.

        The method is only supplied with the staged record and input notebook bundle,
        it then yield results for caching
        """
        for stage_record, nb_bundle in input_iterator:
            uri = nb_bundle.uri
            self.logger.info("Executing: {}".format(uri))
            with tempfile.TemporaryDirectory() as tmpdirname:
                try:
                    asset_files = copy_assets(stage_record, tmpdirname)
                except Exception as err:
                    self.logger.error("Assets Error: {}".format(err), exc_info=True)
                    yield None
                    continue
                timer = Timer()
                try:
                    with timer:
                        # execute notebook, transforming it in-place
                        # TODO does it need to wiped first?
                        executenb(nb_bundle.nb, cwd=tmpdirname)
                except Exception:
                    exc_string = "".join(traceback.format_exc())
                    self.logger.error("Execution Failed: {}".format(uri))
                    yield create_bundle(
                        nb_bundle, tmpdirname, asset_files, timer.last_split, exc_string
                    )
                else:
                    self.logger.info("Execution Succeeded: {}".format(uri))
                    yield create_bundle(
                        nb_bundle, tmpdirname, asset_files, timer.last_split
                    )
