from pathlib import Path
import sys

import click
import tabulate
import yaml

from jupyter_cache.cli.commands.cmd_main import jcache
from jupyter_cache.cli import arguments, options
from jupyter_cache.cache import JupyterCacheBase
from jupyter_cache.base import (  # noqa: F401
    CachingError,
    RetrievalError,
    NbValidityError,
)


def shorten_path(file_path, length):
    """Split the path into separate parts,
    select the last 'length' elements and join them again
    """
    if length is None:
        return Path(file_path)
    return Path(*Path(file_path).parts[-length:])


@jcache.command("clear")
@options.CACHE_PATH
def clear_cache(cache_path):
    """Clear the cache completely."""
    db = JupyterCacheBase(cache_path)
    click.confirm("Are you sure you want to permanently clear the cache!?", abort=True)
    db.clear_cache()
    click.secho("Cache cleared!", fg="green")


@jcache.command("commit-limit")
@options.CACHE_PATH
@click.argument("limit", metavar="COMMIT_LIMIT", type=int)
def change_commit_limit(cache_path, limit):
    """Change the commit limit of the cache (default: 1000)."""
    db = JupyterCacheBase(cache_path)
    db.change_commit_limit(limit)
    click.secho("Limit changed!", fg="green")


def format_commit_record(record, hashkeys, path_length):
    data = {
        "PK": record.pk,
        "URI": str(shorten_path(record.uri, path_length)),
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
@options.PATH_LENGTH
def list_commits(cache_path, hashkeys, path_length):
    """List committed notebook records in the cache."""
    db = JupyterCacheBase(cache_path)
    records = db.list_commit_records()
    if not records:
        click.secho("No Commited Notebooks", fg="blue")
    # TODO optionally list number of artifacts
    click.echo(
        tabulate.tabulate(
            [
                format_commit_record(r, hashkeys, path_length)
                for r in sorted(records, key=lambda r: r.accessed, reverse=True)
            ],
            headers="keys",
        )
    )


@jcache.command("show-commit")
@options.CACHE_PATH
@arguments.PK
def show_commit(cache_path, pk):
    """Show details of a committed notebook in the cache."""
    db = JupyterCacheBase(cache_path)
    record = db.get_commit_record(pk)
    data = format_commit_record(record, True, None)
    click.echo(yaml.safe_dump(data, sort_keys=False), nl=False)
    with db.commit_artefacts_temppath(pk) as folder:
        paths = [str(p.relative_to(folder)) for p in folder.glob("**/*") if p.is_file()]
    if not paths:
        click.echo("")
        return
    click.echo(f"Artifacts:")
    for path in paths:
        click.echo(f"- {path}")


@jcache.command("cat-artifact")
@options.CACHE_PATH
@arguments.PK
@arguments.ARTIFACT_RPATH
def cat_artifact(cache_path, pk, artifact_rpath):
    """Print the contents of a commit artefact."""
    db = JupyterCacheBase(cache_path)
    with db.commit_artefacts_temppath(pk) as path:
        artifact_path = path.joinpath(artifact_rpath)
        if not artifact_path.exists():
            click.secho("Artifact does not exist", fg="red")
            sys.exit(1)
        if not artifact_path.is_file():
            click.secho("Artifact is not a file", fg="red")
            sys.exit(1)
        text = artifact_path.read_text()
    click.echo(text)


def commit_file(db, nbpath, validate, overwrite, artifact_paths=()):
    click.echo("Committing: {}".format(nbpath))
    try:
        db.commit_notebook_file(
            nbpath,
            artifacts=artifact_paths,
            check_validity=validate,
            overwrite=overwrite,
        )
    except NbValidityError as error:
        click.secho("Validity Error: ", fg="red", nl=False)
        click.echo(str(error))
        if click.confirm(
            "The notebook may not have been executed, continue committing?"
        ):
            try:
                db.commit_notebook_file(
                    nbpath,
                    artifacts=artifact_paths,
                    check_validity=False,
                    overwrite=overwrite,
                )
            except IOError as error:
                click.secho("Artifact Error: ", fg="red", nl=False)
                click.echo(str(error))
                return False
    except IOError as error:
        click.secho("Artifact Error: ", fg="red", nl=False)
        click.echo(str(error))
        return False
    return True


@jcache.command("commit-nb")
@arguments.ARTIFACT_PATHS
@options.NB_PATH
@options.CACHE_PATH
@options.VALIDATE_NB
@options.OVERWRITE_COMMIT
def commit_nb(cache_path, artifact_paths, nbpath, validate, overwrite):
    """Commit a notebook that has already been executed, with artifacts."""
    db = JupyterCacheBase(cache_path)
    success = commit_file(db, nbpath, validate, overwrite, artifact_paths)
    if success:
        click.secho("Success!", fg="green")


@jcache.command("commit-nbs")
@arguments.NB_PATHS
@options.CACHE_PATH
@options.VALIDATE_NB
@options.OVERWRITE_COMMIT
def commit_nbs(cache_path, nbpaths, validate, overwrite):
    """Commit notebook(s) that have already been executed."""
    db = JupyterCacheBase(cache_path)
    success = True
    for nbpath in nbpaths:
        # TODO deal with errors (print all at end? or option to ignore)
        if not commit_file(db, nbpath, validate, overwrite):
            success = False
    if success:
        click.secho("Success!", fg="green")


@jcache.command("remove-commits")
@arguments.PKS
@options.CACHE_PATH
@options.REMOVE_ALL
def remove_commits(cache_path, pks, remove_all):
    """Remove notebook commit(s) from the cache by Primary Key."""
    db = JupyterCacheBase(cache_path)
    if remove_all:
        pks = [r.pk for r in db.list_commit_records()]
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
@options.REMOVE_ALL
def unstage_nbs(cache_path, nbpaths, remove_all):
    """Unstage notebook(s) for execution."""
    db = JupyterCacheBase(cache_path)
    if remove_all:
        nbpaths = [record.uri for record in db.list_staged_records()]
    for path in nbpaths:
        # TODO deal with errors (print all at end? or option to ignore)
        click.echo("Unstaging: {}".format(path))
        db.discard_staged_notebook(path)
    click.secho("Success!", fg="green")


def format_staged_record(record, commit, path_length):
    data = {
        "PK": record.pk,
        "URI": shorten_path(record.uri, path_length),
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
@options.PATH_LENGTH
def list_staged(cache_path, compare, path_length):
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
        rows.append(format_staged_record(record, commit, path_length))
    click.echo(tabulate.tabulate(rows, headers="keys"))
