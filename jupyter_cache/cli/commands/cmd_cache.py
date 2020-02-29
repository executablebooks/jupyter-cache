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


@jcache.command("cache-limit")
@options.CACHE_PATH
@click.argument("limit", metavar="CACHE_LIMIT", type=int)
def change_cache_limit(cache_path, limit):
    """Change the maximum number of notebooks stored in the cache."""
    db = JupyterCacheBase(cache_path)
    db.change_cache_limit(limit)
    click.secho("Cache limit changed!", fg="green")


def format_cache_record(record, hashkeys, path_length):
    data = {
        "ID": record.pk,
        "URI": str(shorten_path(record.uri, path_length)),
        "Created": record.created.isoformat(" ", "minutes"),
        "Accessed": record.accessed.isoformat(" ", "minutes"),
        # "Description": record.description,
    }
    if hashkeys:
        data["Hashkey"] = record.hashkey
    return data


@jcache.command("list-cached")
@options.CACHE_PATH
@click.option("-h", "--hashkeys", is_flag=True, help="Whether to show hashkeys.")
@options.PATH_LENGTH
def list_caches(cache_path, hashkeys, path_length):
    """List cached notebook records in the cache."""
    db = JupyterCacheBase(cache_path)
    records = db.list_cache_records()
    if not records:
        click.secho("No Cached Notebooks", fg="blue")
    # TODO optionally list number of artifacts
    click.echo(
        tabulate.tabulate(
            [
                format_cache_record(r, hashkeys, path_length)
                for r in sorted(records, key=lambda r: r.accessed, reverse=True)
            ],
            headers="keys",
        )
    )


@jcache.command("show-cached")
@options.CACHE_PATH
@arguments.PK
def show_cache(cache_path, pk):
    """Show details of a cached notebook in the cache."""
    db = JupyterCacheBase(cache_path)
    record = db.get_cache_record(pk)
    data = format_cache_record(record, True, None)
    click.echo(yaml.safe_dump(data, sort_keys=False), nl=False)
    with db.cache_artefacts_temppath(pk) as folder:
        paths = [str(p.relative_to(folder)) for p in folder.glob("**/*") if p.is_file()]
    if not (paths or record.data):
        click.echo("")
        return
    if paths:
        click.echo(f"Artifacts:")
        for path in paths:
            click.echo(f"- {path}")
    if record.data:
        click.echo(yaml.safe_dump({"Data": record.data}))


@jcache.command("cat-artifact")
@options.CACHE_PATH
@arguments.PK
@arguments.ARTIFACT_RPATH
def cat_artifact(cache_path, pk, artifact_rpath):
    """Print the contents of a cached artefact."""
    db = JupyterCacheBase(cache_path)
    with db.cache_artefacts_temppath(pk) as path:
        artifact_path = path.joinpath(artifact_rpath)
        if not artifact_path.exists():
            click.secho("Artifact does not exist", fg="red")
            sys.exit(1)
        if not artifact_path.is_file():
            click.secho("Artifact is not a file", fg="red")
            sys.exit(1)
        text = artifact_path.read_text()
    click.echo(text)


def cache_file(db, nbpath, validate, overwrite, artifact_paths=()):
    click.echo("Caching: {}".format(nbpath))
    try:
        db.cache_notebook_file(
            nbpath,
            artifacts=artifact_paths,
            check_validity=validate,
            overwrite=overwrite,
        )
    except NbValidityError as error:
        click.secho("Validity Error: ", fg="red", nl=False)
        click.echo(str(error))
        if click.confirm("The notebook may not have been executed, continue caching?"):
            try:
                db.cache_notebook_file(
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


@jcache.command("cache-nb")
@arguments.ARTIFACT_PATHS
@options.NB_PATH
@options.CACHE_PATH
@options.VALIDATE_NB
@options.OVERWRITE_CACHED
def cache_nb(cache_path, artifact_paths, nbpath, validate, overwrite):
    """Cache a notebook that has already been executed."""
    db = JupyterCacheBase(cache_path)
    success = cache_file(db, nbpath, validate, overwrite, artifact_paths)
    if success:
        click.secho("Success!", fg="green")


@jcache.command("cache-nbs")
@arguments.NB_PATHS
@options.CACHE_PATH
@options.VALIDATE_NB
@options.OVERWRITE_CACHED
def cache_nbs(cache_path, nbpaths, validate, overwrite):
    """Cache notebook(s) that have already been executed."""
    db = JupyterCacheBase(cache_path)
    success = True
    for nbpath in nbpaths:
        # TODO deal with errors (print all at end? or option to ignore)
        if not cache_file(db, nbpath, validate, overwrite):
            success = False
    if success:
        click.secho("Success!", fg="green")


@jcache.command("remove-cached")
@arguments.PKS
@options.CACHE_PATH
@options.REMOVE_ALL
def remove_caches(cache_path, pks, remove_all):
    """Remove notebooks stored in the cache."""
    db = JupyterCacheBase(cache_path)
    if remove_all:
        pks = [r.pk for r in db.list_cache_records()]
    for pk in pks:
        # TODO deal with errors (print all at end? or option to ignore)
        click.echo("Removing Cache ID = {}".format(pk))
        try:
            db.remove_cache(pk)
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
    click.echo(db.diff_nbfile_with_cache(pk, nbpath, as_str=True))
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


@jcache.command("stage-nb")
@arguments.ASSET_PATHS
@options.NB_PATH
@options.CACHE_PATH
def stage_nb(cache_path, nbpath, asset_paths):
    """Cache a notebook, with possible assets."""
    db = JupyterCacheBase(cache_path)
    db.stage_notebook_file(nbpath, asset_paths)
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


def format_staged_record(record, cache_record, path_length, assets=True):
    data = {
        "ID": record.pk,
        "URI": str(shorten_path(record.uri, path_length)),
        "Created": record.created.isoformat(" ", "minutes"),
    }
    if assets:
        data["Assets"] = len(record.assets)
    if cache_record:
        data["Cache ID"] = cache_record.pk
    return data


@jcache.command("list-staged")
@options.CACHE_PATH
@click.option(
    "--compare/--no-compare",
    default=True,
    show_default=True,
    help="Compare to cached notebooks (to find cache ID).",
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
        cache_record = None
        if compare:
            cache_record = db.get_cache_record_of_staged(record.uri)
        rows.append(format_staged_record(record, cache_record, path_length))
    click.echo(tabulate.tabulate(rows, headers="keys"))


@jcache.command("show-staged")
@options.CACHE_PATH
@arguments.PK
def show_staged(cache_path, pk):
    """Show details of a staged notebook."""
    db = JupyterCacheBase(cache_path)
    record = db.get_staged_record(pk)
    cache_record = db.get_cache_record_of_staged(record.uri)
    data = format_staged_record(record, cache_record, None, assets=False)
    click.echo(yaml.safe_dump(data, sort_keys=False), nl=False)
    if not record.assets:
        click.echo("")
        return
    click.echo(f"Assets:")
    for path in record.assets:
        click.echo(f"- {path}")
