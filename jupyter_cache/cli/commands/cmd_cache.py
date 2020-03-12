import sys

import click

from jupyter_cache.cli.commands.cmd_main import jcache
from jupyter_cache.cli import arguments, options
from jupyter_cache.cli.utils import shorten_path, get_cache


@jcache.group("cache")
def cmnd_cache():
    """Commands for adding to and inspecting the cache."""
    pass


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


@cmnd_cache.command("list")
@options.CACHE_PATH
@click.option("-h", "--hashkeys", is_flag=True, help="Whether to show hashkeys.")
@options.PATH_LENGTH
def list_caches(cache_path, hashkeys, path_length):
    """List cached notebook records in the cache."""
    import tabulate

    db = get_cache(cache_path)
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


@cmnd_cache.command("show")
@options.CACHE_PATH
@arguments.PK
def show_cache(cache_path, pk):
    """Show details of a cached notebook in the cache."""
    import yaml

    db = get_cache(cache_path)
    try:
        record = db.get_cache_record(pk)
    except KeyError:
        click.secho("ID {} does not exist, Aborting!".format(pk), fg="red")
        sys.exit(1)
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


@cmnd_cache.command("cat-artifact")
@options.CACHE_PATH
@arguments.PK
@arguments.ARTIFACT_RPATH
def cat_artifact(cache_path, pk, artifact_rpath):
    """Print the contents of a cached artefact."""
    db = get_cache(cache_path)
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

    from jupyter_cache.base import NbValidityError

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


@cmnd_cache.command("add-with-artefacts")
@arguments.ARTIFACT_PATHS
@options.NB_PATH
@options.CACHE_PATH
@options.VALIDATE_NB
@options.OVERWRITE_CACHED
def cache_nb(cache_path, artifact_paths, nbpath, validate, overwrite):
    """Cache a notebook, with possible artefact files."""
    db = get_cache(cache_path)
    success = cache_file(db, nbpath, validate, overwrite, artifact_paths)
    if success:
        click.secho("Success!", fg="green")


@cmnd_cache.command("add")
@arguments.NB_PATHS
@options.CACHE_PATH
@options.VALIDATE_NB
@options.OVERWRITE_CACHED
def cache_nbs(cache_path, nbpaths, validate, overwrite):
    """Cache notebook(s) that have already been executed."""
    db = get_cache(cache_path)
    success = True
    for nbpath in nbpaths:
        # TODO deal with errors (print all at end? or option to ignore)
        if not cache_file(db, nbpath, validate, overwrite):
            success = False
    if success:
        click.secho("Success!", fg="green")


@cmnd_cache.command("remove")
@arguments.PKS
@options.CACHE_PATH
@options.REMOVE_ALL
def remove_caches(cache_path, pks, remove_all):
    """Remove notebooks stored in the cache."""
    from jupyter_cache.base import CachingError

    db = get_cache(cache_path)
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


@cmnd_cache.command("diff-nb")
@arguments.PK
@arguments.NB_PATH
@options.CACHE_PATH
def diff_nb(cache_path, pk, nbpath):
    """Print a diff of a notebook to one stored in the cache."""
    db = get_cache(cache_path)
    click.echo(db.diff_nbfile_with_cache(pk, nbpath, as_str=True))
    click.secho("Success!", fg="green")
