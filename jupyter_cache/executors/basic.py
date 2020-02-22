import tempfile

from nbconvert.preprocessors.execute import executenb

# from jupyter_client.kernelspec import get_kernel_spec, NoSuchKernel

from jupyter_cache.executors.base import JupyterExecutorAbstract


class JupyterExecutorBasic(JupyterExecutorAbstract):
    def run(self, uri_filter=None):
        executed_uris = []
        for nb_bundle in self.cache.iter_notebooks_to_exec():
            if uri_filter is not None and nb_bundle.uri not in uri_filter:
                self.logger.info("Skipping: {}".format(nb_bundle.uri))
                continue
            self.logger.info("Executing: {}".format(nb_bundle.uri))
            try:
                with tempfile.TemporaryDirectory() as tmpdirname:
                    executenb(nb_bundle.nb, cwd=tmpdirname)
            except Exception:
                self.logger.error("Failed: {}".format(nb_bundle.uri), exc_info=True)
            else:
                self.logger.info("Success: {}".format(nb_bundle.uri))
                self.cache.stage_notebook_bundle(nb_bundle)
                executed_uris.append(nb_bundle.uri)
        # TODO what should the balance of responsibility be here?
        # Should the executor be adding to the cache,
        # or perhaps run just accepts the iter and returns NbBundles.
        return executed_uris
