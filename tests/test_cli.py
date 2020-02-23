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


def test_stage_nbs(tmp_path):
    db = JupyterCacheGit(str(tmp_path))
    path = os.path.join(NB_PATH, "basic.ipynb")
    runner = CliRunner()
    result = runner.invoke(cmd_cache.stage_nbs, ["-p", tmp_path, path])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output
    assert db.list_staged_notebooks() == {path}


def test_commit_nbs(tmp_path):
    db = JupyterCacheGit(str(tmp_path))
    path = os.path.join(NB_PATH, "basic.ipynb")
    runner = CliRunner()
    result = runner.invoke(
        cmd_cache.commit_nbs, ["-p", tmp_path, "-s", "--no-validate", path]
    )
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output
    assert db.list_committed_notebooks() == {path}


def test_invalidate_nbs(tmp_path):
    db = JupyterCacheGit(str(tmp_path))
    path = os.path.join(NB_PATH, "basic.ipynb")
    db.stage_notebook_file(path)
    db.commit_staged_notebook(path, check_validity=False)
    runner = CliRunner()
    result = runner.invoke(cmd_cache.invalidate_nbs, ["-p", tmp_path, path])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    nbbundle = db.get_staged_notebook(path)
    assert "invalidated" in nbbundle.nb.metadata


def test_list_execution(tmp_path):
    db = JupyterCacheGit(str(tmp_path))
    path = os.path.join(NB_PATH, "basic.ipynb")
    db.stage_notebook_file(path)
    runner = CliRunner()
    result = runner.invoke(cmd_cache.list_execution, ["-p", tmp_path])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output


def test_remove_nbs(tmp_path):
    db = JupyterCacheGit(str(tmp_path))
    path = os.path.join(NB_PATH, "basic.ipynb")
    db.stage_notebook_file(path)
    runner = CliRunner()
    result = runner.invoke(cmd_cache.remove_nbs, ["-p", tmp_path, path])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output
    assert db.list_staged_notebooks() == set()


def test_diff_nbs(tmp_path):
    db = JupyterCacheGit(str(tmp_path))
    path = os.path.join(NB_PATH, "basic.ipynb")
    db.stage_notebook_file(path)
    db.commit_staged_notebook(path, check_validity=False)
    nb_bundle = db.get_committed_notebook(path)
    nb_bundle.nb.cells[0].source = "# New Title"
    db.stage_notebook_bundle(nb_bundle)

    runner = CliRunner()
    result = runner.invoke(cmd_cache.diff_nbs, ["-p", tmp_path, path])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert result.output.splitlines()[2:8] == [
        "--- committed",
        "+++ staged",
        "## inserted before nb/cells/0:",
        "+  markdown cell:",
        "+    source:",
        "+      # New Title",
    ]
