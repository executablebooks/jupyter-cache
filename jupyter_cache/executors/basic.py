import tempfile

from nbconvert.preprocessors.execute import executenb

# from jupyter_client.kernelspec import get_kernel_spec, NoSuchKernel

from jupyter_cache.executors.base import JupyterExecutorAbstract


class JupyterExecutorBasic(JupyterExecutorAbstract):
    def run(self, uri_filter=None):
        executed_uris = []
        for record in self.cache.list_nbs_to_exec():
            uri = record.uri
            if uri_filter is not None and uri not in uri_filter:
                self.logger.info("Skipping: {}".format(uri))
                continue
            self.logger.info("Executing: {}".format(uri))
            nb_bundle = self.cache.get_staged_notebook(uri)
            try:
                with tempfile.TemporaryDirectory() as tmpdirname:
                    executenb(nb_bundle.nb, cwd=tmpdirname)
            except Exception:
                self.logger.error("Failed Execution: {}".format(uri), exc_info=True)
            else:
                try:
                    self.cache.commit_notebook_bundle(nb_bundle, overwrite=True)
                    self.cache.discard_staged_notebook(uri)
                except Exception:
                    self.logger.error("Failed Commit: {}".format(uri), exc_info=True)
                else:
                    self.logger.info("Success: {}".format(uri))
                    executed_uris.append(nb_bundle.uri)
        # TODO what should the balance of responsibility be here?
        # Should the executor be adding to the cache,
        # or perhaps run just accepts the iter and returns NbBundles.
        return executed_uris
