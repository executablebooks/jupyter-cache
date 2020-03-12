from datetime import datetime
from glob import glob
import os
from textwrap import dedent

from click.testing import CliRunner

from jupyter_cache.cli.commands import cmd_main, cmd_cache, cmd_stage, cmd_exec
from jupyter_cache.cache.main import DEFAULT_CACHE_LIMIT


def get_string(cli, group=None, args=(), input=None):
    command_str = ["jcache"] if cli.name != "jcache" else []
    if group:
        command_str.append(group)
    command_str.append(cli.name)
    command_str = " ".join(command_str)

    runner = CliRunner()
    result = runner.invoke(cli, args, input=input)
    root_path = os.getcwd() + os.sep
    return "```console\n$ {}{}\n{}```".format(
        command_str,
        (" " + " ".join(args)) if args else "",
        result.output.replace(root_path, "../"),
    )


def main():

    get_string(cmd_main.clear_cache, input="y")

    strings = []
    strings.append(
        "<!-- This section was auto-generated on {} by: {} -->".format(
            datetime.now().isoformat(" ", "minutes"), __file__
        )
    )
    strings.append("From the checked-out repository folder:")
    strings.append(get_string(cmd_main.jcache, None, ["--help"]))
    strings.append(
        dedent(
            """\
        **Important**: Execute this in the terminal for auto-completion:

        ```console
        eval "$(_JCACHE_COMPLETE=source jcache)"
        ```"""
        )
    )

    # cache
    strings.append("### Caching Executed Notebooks")
    cache_name = cmd_cache.cmnd_cache.name
    strings.append(get_string(cmd_cache.cmnd_cache, None, ["--help"]))
    strings.append("The first time the cache is required, it will be lazily created:")
    strings.append(get_string(cmd_cache.list_caches, cache_name, input="y"))
    strings.append(
        dedent(
            """\
        You can add notebooks straight into the cache.
        When caching, a check will be made that the notebooks look to have been executed
        correctly, i.e. the cell execution counts go sequentially up from 1."""
        )
    )
    strings.append(
        get_string(
            cmd_cache.cache_nbs, cache_name, ["tests/notebooks/basic.ipynb"], input="y"
        )
    )
    strings.append("Or to skip validation:")
    strings.append(
        get_string(
            cmd_cache.cache_nbs,
            cache_name,
            ["--no-validate"] + glob("tests/notebooks/*.ipynb"),
        )
    )
    strings.append(
        dedent(
            """\
        Once you've cached some notebooks, you can look at the 'cache records'
        for what has been cached.

        Each notebook is hashed (code cells and kernel spec only),
        which is used to compare against 'staged' notebooks.
        Multiple hashes for the same URI can be added
        (the URI is just there for inspetion) and the size of the cache is limited
        (current default {}) so that, at this size,
        the last accessed records begin to be deleted.
        You can remove cached records by their ID.""".format(
                DEFAULT_CACHE_LIMIT
            )
        )
    )
    strings.append(get_string(cmd_cache.list_caches, cache_name))
    strings.append(
        dedent(
            """\
        You can also cache notebooks with artefacts
        (external outputs of the notebook execution)."""
        )
    )
    strings.append(
        get_string(
            cmd_cache.cache_nb,
            cache_name,
            [
                "-nb",
                "tests/notebooks/basic.ipynb",
                "tests/notebooks/artifact_folder/artifact.txt",
            ],
            input="y",
        )
    )
    strings.append(
        "Show a full description of a cached notebook by referring to its ID"
    )
    strings.append(get_string(cmd_cache.show_cache, cache_name, ["6"]))
    strings.append("Note artefact paths must be 'upstream' of the notebook folder:")
    strings.append(
        get_string(
            cmd_cache.cache_nb,
            cache_name,
            ["-nb", "tests/notebooks/basic.ipynb", "tests/test_db.py"],
        )
    )
    strings.append("To view the contents of an execution artefact:")
    strings.append(
        get_string(
            cmd_cache.cat_artifact, cache_name, ["6", "artifact_folder/artifact.txt"]
        )
    )
    strings.append("You can directly remove a cached notebook by its ID:")
    strings.append(get_string(cmd_cache.remove_caches, cache_name, ["4"]))
    strings.append(
        "You can also diff any of the cached notebooks with any (external) notebook:"
    )
    strings.append(
        get_string(cmd_cache.diff_nb, cache_name, ["2", "tests/notebooks/basic.ipynb"])
    )

    # staging
    strings.append("### Staging Notebooks for execution")
    stage_name = cmd_stage.cmnd_stage.name
    strings.append(get_string(cmd_stage.cmnd_stage, None, ["--help"]))
    strings.append(
        dedent(
            """\
        Staged notebooks are recorded as pointers to their URI,
        i.e. no physical copying takes place until execution time.

        If you stage some notebooks for execution, then
        you can list them to see which have existing records in the cache (by hash),
        and which will require execution:"""
        )
    )
    strings.append(
        get_string(cmd_stage.stage_nbs, stage_name, glob("tests/notebooks/*.ipynb"))
    )
    strings.append(get_string(cmd_stage.list_staged, stage_name))
    strings.append("You can remove a staged notebook by its URI or ID:")
    strings.append(get_string(cmd_stage.unstage_nbs_id, stage_name, ["4"]))
    strings.append("You can then run a basic execution of the required notebooks:")
    strings.append(get_string(cmd_cache.remove_caches, cache_name, ["6", "2"]))
    strings.append(get_string(cmd_exec.execute_nbs, None))
    strings.append(
        dedent(
            """\
        Successfully executed notebooks will be cached to the cache,
        along with any 'artefacts' created by the execution,
        that are inside the notebook folder, and data supplied by the executor."""
        )
    )
    strings.append(get_string(cmd_stage.list_staged, stage_name))
    strings.append(
        "Execution data (such as execution time) will be stored in the cache record:"
    )
    strings.append(get_string(cmd_cache.show_cache, cache_name, ["6"]))
    strings.append(
        "Failed notebooks will not be cached, "
        "but the exception traceback will be added to the stage record:"
    )
    strings.append(get_string(cmd_stage.show_staged, stage_name, ["2"]))
    strings.append(
        "Once executed you may leave staged notebooks, "
        "for later re-execution, or remove them:"
    )
    strings.append(
        get_string(cmd_stage.unstage_nbs_id, stage_name, ["--all"], input="y")
    )

    # assets
    strings.append(
        dedent(
            """\
        You can also stage notebooks with assets;
        external files that are required by the notebook during execution.
        As with artefacts, these files must be in the same folder as the notebook,
        or a sub-folder."""
        )
    )
    strings.append(
        get_string(
            cmd_stage.stage_nb,
            stage_name,
            [
                "-nb",
                "tests/notebooks/basic.ipynb",
                "tests/notebooks/artifact_folder/artifact.txt",
            ],
        )
    )
    strings.append(get_string(cmd_stage.show_staged, stage_name, ["1"]))

    return "\n\n".join(strings)


if __name__ == "__main__":
    print(main())
