import os
import click


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
