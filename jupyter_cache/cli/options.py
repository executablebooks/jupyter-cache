import os
import click


def callback_autocomplete(ctx, param, value):
    if value and not ctx.resilient_parsing:
        click.echo("Execute this in the terminal for auto-completion:")
        click.echo('eval "$(_JCACHE_COMPLETE=source jcache)"')
        ctx.exit()


AUTOCOMPLETE = click.option(
    "-a",
    "--autocomplete",
    help="Print the autocompletion command and exit.",
    is_flag=True,
    expose_value=True,
    is_eager=True,
    callback=callback_autocomplete,
)


def default_cache_path():
    return os.environ.get("JUPYTERCACHE", os.path.join(os.getcwd(), ".jupyter_cache"))


def callback_print_cache_path(ctx, param, value):
    if value and not ctx.resilient_parsing:
        click.secho("Cache path: ", fg="green", nl=False)
        click.echo(default_cache_path())
        ctx.exit()


PRINT_CACHE_PATH = click.option(
    "-p",
    "--cache-path",
    help="Print the current cache path and exit.",
    is_flag=True,
    expose_value=True,
    is_eager=True,
    callback=callback_print_cache_path,
)


def check_cache_exists(ctx, param, value):
    if os.path.exists(value):
        return value
    click.secho("Cache path: ", fg="green", nl=False)
    click.echo(value)
    if not click.confirm("The cache does not yet exist, do you want to create it?"):
        click.secho("Aborted!", bold=True, fg="red")
        ctx.exit()
    return value


CACHE_PATH = click.option(
    "-p",
    "--cache-path",
    help="Path to cache.",
    default=default_cache_path,
    show_default=".jupyter_cache",
    callback=check_cache_exists,
)


NB_PATH = click.option(
    "-nb",
    "--nbpath",
    required=True,
    help="The notebooks path.",
    type=click.Path(dir_okay=False, exists=True, readable=True, resolve_path=True),
)


EXEC_ENTRYPOINT = click.option(
    "-e",
    "--entry-point",
    help="The entry-point from which to load the executor.",
    default="basic",
    show_default=True,
)

EXEC_TIMEOUT = click.option(
    "-t",
    "--timeout",
    help="Execution timeout value in seconds.",
    default=30,
    show_default=True,
)


PATH_LENGTH = click.option(
    "-l", "--path-length", default=3, show_default=True, help="Maximum URI path."
)


VALIDATE_NB = click.option(
    "--validate/--no-validate",
    default=True,
    show_default=True,
    help="Whether to validate that a notebook has been executed.",
)


OVERWRITE_CACHED = click.option(
    "--overwrite/--no-overwrite",
    default=True,
    show_default=True,
    help="Whether to overwrite an existing notebook with the same hash.",
)


def confirm_remove_all(ctx, param, remove_all):
    if remove_all and not click.confirm("Are you sure you want to remove all?"):
        click.secho("Aborted!", bold=True, fg="red")
        ctx.exit()
    return remove_all


REMOVE_ALL = click.option(
    "-a",
    "--all",
    "remove_all",
    is_flag=True,
    help="Remove all notebooks.",
    callback=confirm_remove_all,
)
