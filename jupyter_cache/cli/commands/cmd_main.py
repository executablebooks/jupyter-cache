"""The main `jcache` click group."""
import click

from jupyter_cache.cli import options


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(
    None, "-v", "--version", message="jupyter-cache version %(version)s"
)
@options.PRINT_CACHE_PATH
@options.AUTOCOMPLETE
def jcache(*args, **kwargs):
    """The command line interface of jupyter-cache."""


@jcache.command("clear")
@options.CACHE_PATH
@options.FORCE
def clear_cache(cache_path, force):
    """Clear the cache completely."""
    from jupyter_cache.cache.main import JupyterCacheBase

    db = JupyterCacheBase(cache_path)
    if not force:
        click.confirm(
            "Are you sure you want to permanently clear the cache!?", abort=True
        )
    db.clear_cache()
    click.secho("Cache cleared!", fg="green")
