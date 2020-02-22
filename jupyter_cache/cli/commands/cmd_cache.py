import click

from jupyter_cache.cli.commands.cmd_main import jcache
from jupyter_cache.cli import arguments, options
from jupyter_cache.git_cache import JupyterCacheGit
from jupyter_cache.base import (  # noqa: F401
    CachingError,
    RetrievalError,
    NbValidityError,
)


@jcache.command("clear")
@options.CACHE_PATH
def clear_cache(cache_path):
    """Clear the cache completely."""
    db = JupyterCacheGit(cache_path)
    click.confirm("Are you sure you want to permanently clear the cache!?", abort=True)
    db.clear_cache()
    click.secho("Cache cleared!", fg="green")


@jcache.command("list-staged")
@options.CACHE_PATH
def list_staged(cache_path):
    """List staged notebook URI's in the cache."""
    db = JupyterCacheGit(cache_path)
    uris = db.list_staged_notebooks()
    if not uris:
        click.secho("No Staged Notebooks", fg="blue")
    for uri in sorted(uris):
        click.echo("- {}".format(uri))


@jcache.command("list-committed")
@options.CACHE_PATH
def list_committed(cache_path):
    """List committed notebook URI's in the cache."""
    db = JupyterCacheGit(cache_path)
    uris = db.list_committed_notebooks()
    if not uris:
        click.secho("No Commited Notebooks", fg="blue")
    for uri in sorted(uris):
        click.echo("- {}".format(uri))


@jcache.command("stage-nbs")
@arguments.NB_PATHS
@options.CACHE_PATH
def stage_nbs(cache_path, nbpaths):
    """Stage a notebook(s) for execution."""
    db = JupyterCacheGit(cache_path)
    for path in nbpaths:
        # TODO deal with errors (print all at end? or option to ignore)
        click.echo("Staging: {}".format(path))
        db.stage_notebook_file(path)
    click.secho("Success!", fg="green")


@jcache.command("commit-nbs")
@arguments.NB_PATHS
@options.CACHE_PATH
@click.option(
    "-s",
    "--auto-stage",
    is_flag=True,
    help="Stage any un-staged notebooks, without prompt.",
)
@click.option(
    "--validate/--no-validate",
    default=True,
    show_default=True,
    help="Whether to validate that a notebook has been executed.",
)
def commit_nbs(cache_path, nbpaths, auto_stage, validate):
    """Commit a notebook(s) that has already been executed."""
    db = JupyterCacheGit(cache_path)
    for path in nbpaths:
        # TODO deal with errors (print all at end? or option to ignore)
        click.echo("Committing: {}".format(path))
        if path not in db.list_staged_notebooks():
            if auto_stage or click.confirm(
                "The notebook has not yet been staged, continue committing?"
            ):
                db.stage_notebook_file(path)
            else:
                continue
        if path not in db.list_staged_notebooks():
            # no changes
            continue
        try:
            db.commit_staged_notebook(path, check_validity=validate)
        except NbValidityError as error:
            click.secho("Validity Error: ", fg="red", nl=False)
            click.echo(str(error))
            if click.confirm(
                "The notebook may not have been executed, continue committing?"
            ):
                db.commit_staged_notebook(path, check_validity=False)
            else:
                continue

    click.secho("Success!", fg="green")


@jcache.command("diff-nbs")
@arguments.NB_PATHS
@options.CACHE_PATH
def diff_nbs(cache_path, nbpaths):
    """Print a diff of a notebook(s) to its staged copy."""
    db = JupyterCacheGit(cache_path)
    for path in nbpaths:
        # TODO deal with errors (print all at end? or option to ignore)
        click.echo(db.diff_staged_notebook(path, as_str=True))
    click.secho("Success!", fg="green")


@jcache.command("invalidate-nbs")
@arguments.NB_PATHS
@options.CACHE_PATH
def invalidate_nbs(cache_path, nbpaths):
    """Invalidate a notebook(s) to signal it for re-execution."""
    db = JupyterCacheGit(cache_path)
    for path in nbpaths:
        # TODO deal with errors (print all at end? or option to ignore)
        click.echo("Invalidating: {}".format(path))
        db.invalidate_notebook(path)
    click.secho("Success!", fg="green")


@jcache.command("remove-nbs")
@arguments.NB_PATHS
@options.CACHE_PATH
def remove_nbs(cache_path, nbpaths):
    """Remove a notebook(s) from the cache."""
    db = JupyterCacheGit(cache_path)
    for path in nbpaths:
        # TODO deal with errors (print all at end? or option to ignore)
        click.echo("Removing: {}".format(path))
        try:
            db.remove_notebook(path)
        except RetrievalError:
            click.secho("Does not exist", fg="red")
        except CachingError as err:
            click.secho("Error: ", fg="red")
            click.echo(str(err))
    click.secho("Success!", fg="green")


@jcache.command("list-execution")
@options.CACHE_PATH
def list_execution(cache_path):
    """List notebook(s) that require re-execution."""
    db = JupyterCacheGit(cache_path)
    uris = [nb_bundle.uri for nb_bundle in db.iter_notebooks_to_exec()]
    if not uris:
        click.secho("No Notebooks Require Execution", fg="blue")
    for uri in sorted(uris):
        click.echo("- {}".format(uri))
