import click
import tabulate

from jupyter_cache.cli.commands.cmd_main import jcache
from jupyter_cache.cli import arguments, options
from jupyter_cache.cache import JupyterCacheBase
from jupyter_cache.base import (  # noqa: F401
    CachingError,
    RetrievalError,
    NbValidityError,
)


@jcache.command("clear")
@options.CACHE_PATH
def clear_cache(cache_path):
    """Clear the cache completely."""
    db = JupyterCacheBase(cache_path)
    click.confirm("Are you sure you want to permanently clear the cache!?", abort=True)
    db.clear_cache()
    click.secho("Cache cleared!", fg="green")


@jcache.command("change-size")
@options.CACHE_PATH
@click.argument("size", metavar="COMMIT_LIMIT", type=int)
def change_size(cache_path, size):
    """Change the commit limit of the cache (default: 1000)."""
    db = JupyterCacheBase(cache_path)
    db.change_cache_size(size)
    click.secho("Limit changed!", fg="green")


def format_commit_record(record, hashkeys):
    data = {
        "PK": record.pk,
        "URI": record.uri,
        "Created": record.created.isoformat(" ", "minutes"),
        "Accessed": record.accessed.isoformat(" ", "minutes"),
        # "Description": record.description,
    }
    if hashkeys:
        data["Hashkey"] = record.hashkey
    return data


@jcache.command("list-commits")
@options.CACHE_PATH
@click.option("-h", "--hashkeys", is_flag=True, help="Whether to show hashkeys.")
def list_commits(cache_path, hashkeys):
    """List committed notebook URI's in the cache."""
    db = JupyterCacheBase(cache_path)
    records = db.list_commit_records()
    if not records:
        click.secho("No Commited Notebooks", fg="blue")
    click.echo(
        tabulate.tabulate(
            [
                format_commit_record(r, hashkeys)
                for r in sorted(records, key=lambda r: r.accessed, reverse=True)
            ],
            headers="keys",
        )
    )


@jcache.command("commit-nbs")
@arguments.NB_PATHS
@options.CACHE_PATH
@click.option(
    "--validate/--no-validate",
    default=True,
    show_default=True,
    help="Whether to validate that a notebook has been executed.",
)
@click.option(
    "--overwrite/--no-overwrite",
    default=True,
    show_default=True,
    help="Whether to overwrite an existing notebook with the same hash.",
)
def commit_nbs(cache_path, nbpaths, validate, overwrite):
    """Commit notebook(s) that have already been executed."""
    db = JupyterCacheBase(cache_path)
    for path in nbpaths:
        # TODO deal with errors (print all at end? or option to ignore)
        click.echo("Committing: {}".format(path))
        try:
            db.commit_notebook_file(path, check_validity=validate, overwrite=overwrite)
        except NbValidityError as error:
            click.secho("Validity Error: ", fg="red", nl=False)
            click.echo(str(error))
            if click.confirm(
                "The notebook may not have been executed, continue committing?"
            ):
                db.commit_notebook_file(path, check_validity=False, overwrite=overwrite)
            else:
                continue

    click.secho("Success!", fg="green")


@jcache.command("remove-commits")
@arguments.PKS
@options.CACHE_PATH
def remove_commits(cache_path, pks):
    """Remove notebook commit(s) from the cache by Primary Key."""
    db = JupyterCacheBase(cache_path)
    for pk in pks:
        # TODO deal with errors (print all at end? or option to ignore)
        click.echo("Removing PK = {}".format(pk))
        try:
            db.remove_commit(pk)
        except KeyError:
            click.secho("Does not exist", fg="red")
        except CachingError as err:
            click.secho("Error: ", fg="red")
            click.echo(str(err))
    click.secho("Success!", fg="green")


@jcache.command("diff-nb")
@arguments.PK
@arguments.NB_PATH
@options.CACHE_PATH
def diff_nb(cache_path, pk, nbpath):
    """Print a diff of a notebook to one stored in the cache."""
    db = JupyterCacheBase(cache_path)
    click.echo(db.diff_nbfile_with_commit(pk, nbpath, as_str=True))
    click.secho("Success!", fg="green")


@jcache.command("stage-nbs")
@arguments.NB_PATHS
@options.CACHE_PATH
def stage_nbs(cache_path, nbpaths):
    """Stage notebook(s) for execution."""
    db = JupyterCacheBase(cache_path)
    for path in nbpaths:
        # TODO deal with errors (print all at end? or option to ignore)
        click.echo("Staging: {}".format(path))
        db.stage_notebook_file(path)
    click.secho("Success!", fg="green")


@jcache.command("unstage-nbs")
@arguments.NB_PATHS
@options.CACHE_PATH
def unstage_nbs(cache_path, nbpaths):
    """Unstage notebook(s) for execution."""
    db = JupyterCacheBase(cache_path)
    for path in nbpaths:
        # TODO deal with errors (print all at end? or option to ignore)
        click.echo("Unstaging: {}".format(path))
        db.discard_staged_notebook(path)
    click.secho("Success!", fg="green")


def format_staged_record(record, commit):
    data = {
        "PK": record.pk,
        "URI": record.uri,
        "Created": record.created.isoformat(" ", "minutes"),
    }
    if commit:
        data["Commit Pk"] = commit.pk
    return data


@jcache.command("list-staged")
@options.CACHE_PATH
@click.option(
    "--compare/--no-compare",
    default=True,
    show_default=True,
    help="Compare to committed notebooks (to find PK).",
)
def list_staged(cache_path, compare):
    """List notebooks staged for possible execution."""
    db = JupyterCacheBase(cache_path)
    records = db.list_staged_records()
    if not records:
        click.secho("No Staged Notebooks", fg="blue")
    rows = []
    for record in sorted(records, key=lambda r: r.created, reverse=True):
        commit = None
        if compare:
            commit = db.get_commit_record_of_staged(record.uri)
        rows.append(format_staged_record(record, commit))
    click.echo(tabulate.tabulate(rows, headers="keys"))
