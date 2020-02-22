import os
import click


def callback_autocomplete(ctx, param, value):
    if value and not ctx.resilient_parsing:
        click.echo("Run this in the terminal for auto-completion:")
        click.echo('eval "$(_JCACHE_COMPLETE=source jcache)"')
        ctx.exit()


AUTOCOMPLETE = click.option(
    "-a",
    "--autocomplete",
    help="Print the terminal autocompletion command and exit.",
    is_flag=True,
    expose_value=True,
    is_eager=True,
    callback=callback_autocomplete,
)


def check_cache_exists(ctx, param, value):
    click.secho("Cache path: ", fg="green", nl=False)
    click.echo(value)
    if os.path.exists(value):
        return value
    if not click.confirm("The cache does not yet exist, do you want to create it?"):
        click.secho("Aborted!", bold=True, fg="red")
        ctx.exit()
    return value


CACHE_PATH = click.option(
    "-p",
    "--cache-path",
    help="Path to cache.",
    default=lambda: os.environ.get(
        "JUPYTERCACHE", os.path.join(os.getcwd(), ".jupyter_cache")
    ),
    show_default=".jupyter_cache",
    callback=check_cache_exists,
)


EXEC_ENTRYPOINT = click.option(
    "-e",
    "--entry-point",
    help="The entry-point from which to load the executor.",
    default="basic",
    show_default=True,
)
