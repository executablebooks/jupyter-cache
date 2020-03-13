import click

from jupyter_cache import get_cache
from jupyter_cache.cli.commands.cmd_main import jcache
from jupyter_cache.cli import options


@jcache.group("config")
def cmnd_config():
    """Commands for configuring the cache."""
    pass


@cmnd_config.command("cache-limit")
@options.CACHE_PATH
@click.argument("limit", metavar="CACHE_LIMIT", type=int)
def change_cache_limit(cache_path, limit):
    """Change the maximum number of notebooks stored in the cache."""
    db = get_cache(cache_path)
    db.change_cache_limit(limit)
    click.secho("Cache limit changed!", fg="green")
