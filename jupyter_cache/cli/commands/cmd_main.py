"""The main `jcache` click group."""
import click


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(
    None, "-v", "--version", message="jupyter-cache version %(version)s"
)
# @options.AUTOCOMPLETE  # doesn't allow file path autocompletion
def jcache():
    """The command line interface of jupyter-cache."""
