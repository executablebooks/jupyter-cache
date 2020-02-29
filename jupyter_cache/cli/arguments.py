import click

NB_PATH = click.argument(
    "nbpath",
    metavar="NBPATH",
    type=click.Path(dir_okay=False, exists=True, readable=True, resolve_path=True),
)

NB_PATHS = click.argument(
    "nbpaths",
    metavar="NBPATHS",
    nargs=-1,
    type=click.Path(dir_okay=False, exists=True, readable=True, resolve_path=True),
)

ARTIFACT_PATHS = click.argument(
    "artifact_paths",
    metavar="ARTIFACT_PATHS",
    nargs=-1,
    type=click.Path(dir_okay=False, exists=True, readable=True, resolve_path=True),
)

ARTIFACT_RPATH = click.argument("artifact_rpath", metavar="ARTIFACT_RPATH", type=str)


ASSET_PATHS = click.argument(
    "asset_paths",
    metavar="ASSET_PATHS",
    nargs=-1,
    type=click.Path(dir_okay=False, exists=True, readable=True, resolve_path=True),
)


PK = click.argument("pk", metavar="ID", type=int)

PKS = click.argument("pks", metavar="IDs", nargs=-1, type=int)
