from pathlib import Path
import tempfile

from nbconvert.preprocessors.execute import executenb

# from jupyter_client.kernelspec import get_kernel_spec, NoSuchKernel

from jupyter_cache.executors.base import JupyterExecutorAbstract
from jupyter_cache.cache.main import NbBundleIn, NbArtifacts


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
                # TODO add assets, and also disciminate between assets and artefacts
                # after execution
                try:
                    executenb(nb_bundle.nb, cwd=tmpdirname)
                except Exception:
                    self.logger.error("Failed Execution: {}".format(uri), exc_info=True)
                else:
                    final_bundle = NbBundleIn(
                        nb_bundle.nb,
                        nb_bundle.uri,
                        NbArtifacts(Path(tmpdirname).glob("**/*"), tmpdirname),
                    )
                    try:
                        self.cache.commit_notebook_bundle(final_bundle, overwrite=True)
                    except Exception:
                        self.logger.error(
                            "Failed Commit: {}".format(uri), exc_info=True
                        )
                    else:
                        self.logger.info("Success: {}".format(uri))
                        succeeded.append(record)
        # TODO what should the balance of responsibility be here?
        # Should the executor be adding to the cache,
        # or perhaps run just accepts the iter and returns NbBundles.
        # TODO it would also be ideal to tag all notebooks
        # that were executed at the same time.
        return succeeded
