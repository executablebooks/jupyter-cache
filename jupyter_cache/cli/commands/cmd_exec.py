import logging
from pathlib import Path

import click

from jupyter_cache import get_cache
from jupyter_cache.cli import arguments, options, utils
from jupyter_cache.cli.commands.cmd_main import jcache
from jupyter_cache.readers import list_readers

logger = logging.getLogger(__name__)
utils.setup_logger(logger)


@jcache.command("execute")
@arguments.PK_OR_PATHS
@options.EXECUTOR_KEY
@options.EXEC_TIMEOUT
@options.CACHE_PATH
@options.set_log_level(logger)
def execute_nbs(cache_path, executor, pk_paths, timeout):
    """Execute all or specific outdated notebooks in the project."""
    import yaml

    from jupyter_cache.executors import load_executor

    db = get_cache(cache_path)
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
            record = db.add_nb_to_project(pk_path, reader=reader)
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
