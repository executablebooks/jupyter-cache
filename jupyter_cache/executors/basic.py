import tempfile

from nbconvert.preprocessors.execute import executenb

# from jupyter_client.kernelspec import get_kernel_spec, NoSuchKernel

from jupyter_cache.executors.base import JupyterExecutorAbstract


class JupyterExecutorBasic(JupyterExecutorAbstract):
    def run(self):
        executed_uris = []
        for nb_bundle in self.cache.iter_notebooks_to_exec():
            self.logger.info("Executing: {}".format(nb_bundle.uri))
            try:
                with tempfile.TemporaryDirectory() as tmpdirname:
                    executenb(nb_bundle.nb, cwd=tmpdirname)
            except Exception as err:
                self.logger.error("Failed: {}".format(nb_bundle.uri), exc_info=err)
            else:
                self.logger.info("Success: {}".format(nb_bundle.uri))
                self.cache.stage_notebook_bundle(nb_bundle)
                executed_uris.append(nb_bundle.uri)
        # TODO what should the balance of responsibility be here?
        # Should the executor be adding to the cache,
        # or perhaps run just accepts the iter and returns NbBundles.
        return executed_uris
