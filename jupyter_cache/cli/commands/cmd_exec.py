import logging
from pathlib import Path

import click
import click_log

from jupyter_cache import get_cache
from jupyter_cache.cli import arguments, options
from jupyter_cache.cli.commands.cmd_main import jcache
from jupyter_cache.readers import list_readers

logger = logging.getLogger(__name__)
click_log.basic_config(logger)


@jcache.command("execute")
@arguments.PK_OR_PATHS
@options.EXECUTOR_KEY
@options.EXEC_TIMEOUT
@options.CACHE_PATH
@click_log.simple_verbosity_option(logger)
def execute_nbs(cache_path, executor, pk_paths, timeout):
    """Execute notebooks that are not in the cache or outdated."""
    import yaml

    from jupyter_cache.executors import load_executor

    db = get_cache(cache_path)
    records = []
    unstaged = []
    for pk_path in pk_paths:
        if pk_path.isdigit():
            pk_path = int(pk_path)
            record = db.get_staged_record(int(pk_path))
            records.append(record)
        else:
            try:
                record = db.get_staged_record(str(Path(pk_path).absolute()))
                records.append(record)
            except KeyError:
                if not Path(pk_path).exists():
                    raise FileNotFoundError(f"'{pk_path}' does not exist.")
                unstaged.append(pk_path)
    if unstaged:
        # ask to stage, select reader
        unstaged_string = "\n - ".join(unstaged)
        click.echo(f"Unstaged notebooks specified:\n - {unstaged_string}")
        if not click.confirm("Continue (staging these notebooks first)?"):
            click.secho("Aborted!", bold=True, fg="red")
            raise SystemExit(1)
        reader = click.prompt(
            "Enter the notebook reader to use",
            type=click.Choice(list_readers()),
            show_choices=True,
            default="nbformat",
            show_default=True,
        )
        for pk_path in unstaged:
            record = db.stage_notebook_file(pk_path, reader=reader)
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
    output["up-to-date"] = list(
        {record.uri for record in records}.difference(result.all())
    )
    click.echo(yaml.safe_dump(output, sort_keys=False))
