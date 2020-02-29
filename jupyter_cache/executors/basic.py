from pathlib import Path
import shutil
import tempfile

from nbconvert.preprocessors.execute import executenb

# from jupyter_client.kernelspec import get_kernel_spec, NoSuchKernel

from jupyter_cache.executors.base import JupyterExecutorAbstract
from jupyter_cache.cache.main import NbBundleIn, NbArtifacts
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


class JupyterExecutorBasic(JupyterExecutorAbstract):
    """A basic implementation of an executor."""

    def run(self, uri_filter=None):
        succeeded = []
        for record in self.cache.list_nbs_to_exec():
            uri = record.uri
            if uri_filter is not None and uri not in uri_filter:
                self.logger.info("Skipping: {}".format(uri))
                continue
            self.logger.info("Executing: {}".format(uri))
            nb_bundle = self.cache.get_staged_notebook(uri)
            with tempfile.TemporaryDirectory() as tmpdirname:
                try:
                    asset_files = copy_assets(record, tmpdirname)
                except Exception as err:
                    self.logger.error("Assets Error: {}".format(err), exc_info=True)
                    continue
                timer = Timer()
                try:
                    with timer:
                        executenb(nb_bundle.nb, cwd=tmpdirname)
                except Exception:
                    self.logger.error("Failed Execution: {}".format(uri), exc_info=True)
                    continue
                final_bundle = NbBundleIn(
                    nb_bundle.nb,
                    nb_bundle.uri,
                    # TODO retrieve assets that have changed file mtime?
                    artifacts=NbArtifacts(
                        [
                            p
                            for p in Path(tmpdirname).glob("**/*")
                            if p not in asset_files
                        ],
                        tmpdirname,
                    ),
                    data={"execution_seconds": timer.last_split},
                )
                try:
                    self.cache.commit_notebook_bundle(final_bundle, overwrite=True)
                except Exception:
                    self.logger.error("Failed Commit: {}".format(uri), exc_info=True)
                    continue

                self.logger.info("Success: {}".format(uri))
                succeeded.append(record)

        # TODO what should the balance of responsibility be here?
        # Should the executor be adding to the cache,
        # or perhaps run just accepts the iter and returns NbBundles.
        # TODO it would also be ideal to tag all notebooks
        # that were executed at the same time (just part of `data` or separate column?).
        # TODO maybe the status of success/failure could be stored on
        # the stage record (commit_status=Enum('OK', 'FAILED', 'MISSING'))
        # also failed notebooks could be stored in the cache, which would be
        # accessed by stage pk (and would be deleted when removing the stage record)
        # see: https://python.quantecon.org/status.html
        return succeeded
