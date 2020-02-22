import logging

import click
import click_log

from jupyter_cache.cli.commands.cmd_main import jcache
from jupyter_cache.cli import options
from jupyter_cache.git_cache import JupyterCacheGit
from jupyter_cache.base import (  # noqa: F401
    CachingError,
    RetrievalError,
    NbValidityError,
)

logger = logging.getLogger(__name__)
click_log.basic_config(logger)


@jcache.command("execute")
@click_log.simple_verbosity_option(logger)
@options.EXEC_ENTRYPOINT
@options.CACHE_PATH
def execute_nbs(cache_path, entry_point):
    """Execute outdated notebooks."""
    from jupyter_cache.executors import load_executor

    db = JupyterCacheGit(cache_path)
    try:
        executor = load_executor("basic", db, logger=logger)
    except ImportError as error:
        logger.error(str(error))
        return 1
    for uri in executor.run():
        db.commit_staged_notebook(uri)
    click.secho("Finished!", fg="green")
