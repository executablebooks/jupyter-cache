import os

from click.testing import CliRunner

from jupyter_cache.git_cache import JupyterCacheGit
from jupyter_cache.cli.commands import cmd_main, cmd_cache

NB_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), "notebooks")


def test_base():
    runner = CliRunner()
    result = runner.invoke(cmd_main.jcache, "-v")
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "jupyter-cache version" in result.output.strip(), result.output


def test_list_staged(tmp_path):
    db = JupyterCacheGit(str(tmp_path))
    db.stage_notebook_file(path=os.path.join(NB_PATH, "basic.ipynb"), uri="basic.ipynb")

    runner = CliRunner()
    result = runner.invoke(cmd_cache.list_staged, ["-p", tmp_path])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output


def test_list_committed(tmp_path):
    db = JupyterCacheGit(str(tmp_path))
    db.stage_notebook_file(path=os.path.join(NB_PATH, "basic.ipynb"), uri="basic.ipynb")
    db.commit_staged_notebook("basic.ipynb", check_validity=False)

    runner = CliRunner()
    result = runner.invoke(cmd_cache.list_committed, ["-p", tmp_path])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output
