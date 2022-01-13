import logging
from pathlib import Path

import click

from jupyter_cache.cli import arguments, options, pass_cache, utils
from jupyter_cache.cli.commands.cmd_main import jcache
from jupyter_cache.readers import list_readers

logger = logging.getLogger(__name__)
utils.setup_logger(logger)


@jcache.group("project")
@options.CACHE_PATH
@pass_cache
def cmnd_project(cache, cache_path):
    """Work with a project."""
    cache.set_cache_path(cache_path)


@cmnd_project.command("version")
@pass_cache
def version(cache):
    """Print the version of the cache."""
    if not cache.cache_path.exists():
        click.secho("No cache found.", fg="red")
        raise click.Abort()
    version = cache.get_cache().get_version()
    if version is None:
        click.secho("Cache version not found", fg="red")
        raise click.Abort()
    click.echo(version)


@cmnd_project.command("clear")
@options.FORCE
@pass_cache
def clear_cache(cache, force):
    """Clear the project cache completely."""
    if not cache.cache_path.exists():
        click.secho("Cache does not exist", fg="green")
        raise click.Abort()
    if not force:
        click.echo(f"Cache path: {cache.cache_path}")
        click.confirm(
            "Are you sure you want to permanently clear the cache!?",
            abort=True,
        )
    cache.get_cache().clear_cache()
    click.secho("Cache cleared!", fg="green")


@cmnd_project.command("cache-limit")
@click.argument("limit", metavar="CACHE_LIMIT", type=int, required=False)
@pass_cache
def change_cache_limit(cache, limit):
    """Get/set maximum number of notebooks stored in the cache."""
    db = cache.get_cache()
    if limit is None:
        limit = db.get_cache_limit()
        click.echo(f"Current cache limit: {limit}")
    else:
        db.change_cache_limit(limit)
        click.secho("Cache limit changed!", fg="green")


@cmnd_project.command("execute")
@arguments.PK_OR_PATHS
@options.EXECUTOR_KEY
@options.EXEC_TIMEOUT
@options.set_log_level(logger)
@pass_cache
def execute_nbs(cache, executor, pk_paths, timeout):
    """Execute all or specific outdated notebooks in the project."""
    import yaml

    from jupyter_cache.executors import load_executor

    db = cache.get_cache()
    records = []
    not_in_project = []
    for pk_path in pk_paths:
        if pk_path.isdigit():
            pk_path = int(pk_path)
            record = db.get_project_record(int(pk_path))
            records.append(record)
        else:
            try:
                record = db.get_project_record(str(Path(pk_path).absolute()))
                records.append(record)
            except KeyError:
                if not Path(pk_path).exists():
                    raise FileNotFoundError(f"'{pk_path}' does not exist.")
                not_in_project.append(pk_path)
    if not_in_project:
        not_in_project_string = "\n - ".join(not_in_project)
        click.echo(f"Notebooks not in project:\n - {not_in_project_string}")
        if not click.confirm("Continue (adding these files to the project)?"):
            click.secho("Aborted!", bold=True, fg="red")
            raise SystemExit(1)
        reader = click.prompt(
            "Enter the notebook reader to use",
            type=click.Choice(list_readers()),
            show_choices=True,
            default="nbformat",
            show_default=True,
        )
        for pk_path in not_in_project:
            record = db.add_nb_to_project(
                pk_path, read_data={"name": reader, "type": "plugin"}
            )
            records.append(record)
    try:
        executor = load_executor(executor, db, logger=logger)
    except ImportError as error:
        logger.error(str(error))
        return 1
    result = executor.run_and_cache(
        filter_pks=[record.pk for record in records] or None, timeout=timeout
    )
    click.secho(
        "Finished! Successfully executed notebooks have been cached.", fg="green"
    )
    output = result.as_json()
    if records:
        output["up-to-date"] = list(
            {record.uri for record in records}.difference(result.all())
        )
    click.echo(yaml.safe_dump(output, sort_keys=False))
