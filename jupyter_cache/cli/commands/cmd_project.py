import os
import sys

import click
import nbformat

from jupyter_cache import get_cache
from jupyter_cache.cli import arguments, options
from jupyter_cache.cli.commands.cmd_main import jcache
from jupyter_cache.utils import tabulate_project_records


@jcache.group("project")
def cmnd_project():
    """Commands for interacting with a project."""


@cmnd_project.command("add")
@arguments.NB_PATHS
@options.READER_KEY
@options.CACHE_PATH
def add_notebooks(cache_path, nbpaths, reader):
    """Add notebook(s) to the project."""
    db = get_cache(cache_path)
    for path in nbpaths:
        # TODO deal with errors (print all at end? or option to ignore)
        click.echo("Adding: {}".format(path))
        db.add_nb_to_project(path, reader=reader)
    click.secho("Success!", fg="green")


@cmnd_project.command("add-with-assets")
@arguments.ASSET_PATHS
@options.NB_PATH
@options.READER_KEY
@options.CACHE_PATH
def add_notebook(cache_path, nbpath, reader, asset_paths):
    """Add notebook(s) to the project, with possible asset files."""
    db = get_cache(cache_path)
    db.add_nb_to_project(nbpath, reader=reader, assets=asset_paths)
    click.secho("Success!", fg="green")


@cmnd_project.command("clear")
@options.CACHE_PATH
@options.FORCE
def clear_nbs(cache_path, force):
    """Remove all notebooks from the project."""
    db = get_cache(cache_path)
    if not force:
        click.confirm(
            "Are you sure you want to permanently clear the project!?", abort=True
        )
    for record in db.list_project_records():
        db.remove_nb_from_project(record.pk)
    click.secho("Project cleared!", fg="green")


@cmnd_project.command("remove")
@arguments.PK_OR_PATHS
@options.CACHE_PATH
def remove_nbs(cache_path, pk_paths):
    """Remove notebook(s) from the project (by ID/URI)."""
    db = get_cache(cache_path)
    for pk_path in pk_paths:
        # TODO deal with errors (print all at end? or option to ignore)
        click.echo("Removing: {}".format(pk_path))
        db.remove_nb_from_project(
            int(pk_path) if pk_path.isdigit() else os.path.abspath(pk_path)
        )
    click.secho("Success!", fg="green")


@cmnd_project.command("list")
@options.CACHE_PATH
# @click.option(
#     "--compare/--no-compare",
#     default=True,
#     show_default=True,
#     help="Compare to cached notebooks (to find cache ID).",
# )
@options.PATH_LENGTH
@click.option(
    "--assets",
    is_flag=True,
    help="Show the number of assets associated with each notebook",
)
def list_nbs_in_project(cache_path, path_length, assets):
    """List notebooks in the project."""
    db = get_cache(cache_path)
    records = db.list_project_records()
    if not records:
        click.secho("No notebooks in project", fg="blue")
    click.echo(
        tabulate_project_records(
            records, path_length=path_length, cache=db, assets=assets
        )
    )


@cmnd_project.command("show")
@options.CACHE_PATH
@arguments.PK_OR_PATH
@click.option(
    "--tb/--no-tb",
    default=True,
    show_default=True,
    help="Show traceback, if last execution failed.",
)
def show_project_record(cache_path, pk_path, tb):
    """Show details of a notebook (by ID)."""
    import yaml

    db = get_cache(cache_path)
    try:
        record = db.get_project_record(
            int(pk_path) if pk_path.isdigit() else os.path.abspath(pk_path)
        )
    except KeyError:
        click.secho("ID {} does not exist, Aborting!".format(pk_path), fg="red")
        sys.exit(1)
    cache_record = db.get_cached_project_nb(record.uri)
    data = record.format_dict(cache_record=cache_record, path_length=None, assets=False)
    click.echo(yaml.safe_dump(data, sort_keys=False).rstrip())
    if record.assets:
        click.echo("Assets:")
        for path in record.assets:
            click.echo(f"- {path}")
    if record.traceback:
        click.secho("Failed Last Execution!", fg="red")
        if tb:
            click.echo(record.traceback)


@cmnd_project.command("merge")
@arguments.PK_OR_PATH
@arguments.OUTPUT_PATH
@options.CACHE_PATH
def merge_executed(cache_path, pk_path, outpath):
    """Write notebook merged with cached outputs (by ID/URI)."""
    db = get_cache(cache_path)
    nb = db.get_project_notebook(
        int(pk_path) if pk_path.isdigit() else os.path.abspath(pk_path)
    ).nb
    cached_pk, nb = db.merge_match_into_notebook(nb)
    nbformat.write(nb, outpath)
    click.echo(f"Merged with cache PK {cached_pk}")
    click.secho("Success!", fg="green")
