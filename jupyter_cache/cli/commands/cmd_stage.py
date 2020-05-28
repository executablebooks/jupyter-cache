import sys

import click

from jupyter_cache import get_cache
from jupyter_cache.cli.commands.cmd_main import jcache
from jupyter_cache.cli import arguments, options
from jupyter_cache.utils import tabulate_stage_records


@jcache.group("stage")
def cmnd_stage():
    """Commands for staging notebooks to be executed."""
    pass


@cmnd_stage.command("add")
@arguments.NB_PATHS
@options.CACHE_PATH
def stage_nbs(cache_path, nbpaths):
    """Stage notebook(s) for execution."""
    db = get_cache(cache_path)
    for path in nbpaths:
        # TODO deal with errors (print all at end? or option to ignore)
        click.echo("Staging: {}".format(path))
        db.stage_notebook_file(path)
    click.secho("Success!", fg="green")


@cmnd_stage.command("add-with-assets")
@arguments.ASSET_PATHS
@options.NB_PATH
@options.CACHE_PATH
def stage_nb(cache_path, nbpath, asset_paths):
    """Stage a notebook, with possible asset files."""
    db = get_cache(cache_path)
    db.stage_notebook_file(nbpath, asset_paths)
    click.secho("Success!", fg="green")


@cmnd_stage.command("remove-uris")
@arguments.NB_PATHS
@options.CACHE_PATH
@options.REMOVE_ALL
def unstage_nbs_uri(cache_path, nbpaths, remove_all):
    """Un-stage notebook(s), by URI."""
    db = get_cache(cache_path)
    if remove_all:
        nbpaths = [record.uri for record in db.list_staged_records()]
    for path in nbpaths:
        # TODO deal with errors (print all at end? or option to ignore)
        click.echo("Unstaging: {}".format(path))
        db.discard_staged_notebook(path)
    click.secho("Success!", fg="green")


@cmnd_stage.command("remove-ids")
@arguments.PKS
@options.CACHE_PATH
@options.REMOVE_ALL
def unstage_nbs_id(cache_path, pks, remove_all):
    """Un-stage notebook(s), by ID."""
    db = get_cache(cache_path)
    if remove_all:
        pks = [record.pk for record in db.list_staged_records()]
    for pk in pks:
        # TODO deal with errors (print all at end? or option to ignore)
        click.echo("Unstaging ID: {}".format(pk))
        db.discard_staged_notebook(pk)
    click.secho("Success!", fg="green")


@cmnd_stage.command("list")
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
    db = get_cache(cache_path)
    records = db.list_staged_records()
    if not records:
        click.secho("No Staged Notebooks", fg="blue")
    click.echo(tabulate_stage_records(records, path_length=path_length, cache=db))


@cmnd_stage.command("show")
@options.CACHE_PATH
@arguments.PK
@click.option(
    "--tb/--no-tb",
    default=True,
    show_default=True,
    help="Show traceback, if last execution failed.",
)
def show_staged(cache_path, pk, tb):
    """Show details of a staged notebook."""
    import yaml

    db = get_cache(cache_path)
    try:
        record = db.get_staged_record(pk)
    except KeyError:
        click.secho("ID {} does not exist, Aborting!".format(pk), fg="red")
        sys.exit(1)
    cache_record = db.get_cache_record_of_staged(record.uri)
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
