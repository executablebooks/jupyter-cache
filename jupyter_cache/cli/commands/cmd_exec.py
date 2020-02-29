import logging

import click
import click_log

from jupyter_cache.cli.commands.cmd_main import jcache
from jupyter_cache.cli import arguments, options
from jupyter_cache.cli.utils import get_cache

logger = logging.getLogger(__name__)
click_log.basic_config(logger)


@jcache.command("execute")
@click_log.simple_verbosity_option(logger)
@options.EXEC_ENTRYPOINT
@options.CACHE_PATH
@arguments.PKS
def execute_nbs(cache_path, entry_point, pks):
    """Execute staged notebooks that are outdated."""
    import yaml
    from jupyter_cache.executors import load_executor

    db = get_cache(cache_path)
    try:
        executor = load_executor("basic", db, logger=logger)
    except ImportError as error:
        logger.error(str(error))
        return 1
    result = executor.run_and_cache(filter_pks=pks or None)
    click.secho("Finished!", fg="green")
    click.echo(yaml.safe_dump(result, sort_keys=False))
