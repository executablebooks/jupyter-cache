import click

click.Argument
NB_PATHS = click.argument(
    "nbpaths",
    metavar="NBPATHS",
    nargs=-1,
    type=click.Path(dir_okay=False, exists=True, readable=True, resolve_path=True),
)
