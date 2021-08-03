import os

from click.testing import CliRunner

from jupyter_cache.cache.main import JupyterCacheBase
from jupyter_cache.cli.commands import cmd_cache, cmd_exec, cmd_main, cmd_project

NB_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), "notebooks")


def test_base():
    runner = CliRunner()
    result = runner.invoke(cmd_main.jcache, "-v")
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "jupyter-cache version" in result.output.strip(), result.output


def test_clear_cache(tmp_path):
    JupyterCacheBase(str(tmp_path))
    runner = CliRunner()
    result = runner.invoke(cmd_main.clear_cache, ["-p", tmp_path], input="y")
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "Cache cleared!" in result.output.strip(), result.output


def test_list_caches(tmp_path):
    db = JupyterCacheBase(str(tmp_path))
    db.cache_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"),
        uri="basic.ipynb",
        check_validity=False,
    )
    runner = CliRunner()
    result = runner.invoke(cmd_cache.list_caches, ["-p", tmp_path])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output


def test_list_caches_latest_only(tmp_path):
    db = JupyterCacheBase(str(tmp_path))
    db.cache_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"),
        uri="basic.ipynb",
        check_validity=False,
    )
    db.cache_notebook_file(
        path=os.path.join(NB_PATH, "complex_outputs.ipynb"),
        uri="basic.ipynb",
        check_validity=False,
    )
    runner = CliRunner()
    result = runner.invoke(cmd_cache.list_caches, ["-p", tmp_path])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert len(result.output.strip().splitlines()) == 4, result.output
    result = runner.invoke(cmd_cache.list_caches, ["-p", tmp_path, "--latest-only"])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert len(result.output.strip().splitlines()) == 3, result.output


def test_cache_with_artifact(tmp_path):
    JupyterCacheBase(str(tmp_path))
    nb_path = os.path.join(NB_PATH, "basic.ipynb")
    a_path = os.path.join(NB_PATH, "artifact_folder", "artifact.txt")
    runner = CliRunner()
    result = runner.invoke(
        cmd_cache.cache_nb, ["-p", tmp_path, "--no-validate", "-nb", nb_path, a_path]
    )
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output
    result = runner.invoke(cmd_cache.show_cache, ["-p", tmp_path, "1"])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "- artifact_folder/artifact.txt" in result.output.strip(), result.output
    result = runner.invoke(
        cmd_cache.cat_artifact, ["-p", tmp_path, "1", "artifact_folder/artifact.txt"]
    )
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "An artifact" in result.output.strip(), result.output


def test_cache_nbs(tmp_path):
    db = JupyterCacheBase(str(tmp_path))
    path = os.path.join(NB_PATH, "basic.ipynb")
    runner = CliRunner()
    result = runner.invoke(cmd_cache.cache_nbs, ["-p", tmp_path, "--no-validate", path])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output
    assert db.list_cache_records()[0].uri == path


def test_remove_caches(tmp_path):
    db = JupyterCacheBase(str(tmp_path))
    db.cache_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"),
        uri="basic.ipynb",
        check_validity=False,
    )
    runner = CliRunner()
    result = runner.invoke(cmd_cache.remove_caches, ["-p", tmp_path, "1"])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "Success" in result.output.strip(), result.output
    assert db.list_cache_records() == []


def test_diff_nbs(tmp_path):
    db = JupyterCacheBase(str(tmp_path))
    path = os.path.join(NB_PATH, "basic.ipynb")
    path2 = os.path.join(NB_PATH, "basic_failing.ipynb")
    db.cache_notebook_file(path, check_validity=False)
    # nb_bundle = db.get_cache_bundle(1)
    # nb_bundle.nb.cells[0].source = "# New Title"
    # db.stage_notebook_bundle(nb_bundle)

    runner = CliRunner()
    result = runner.invoke(cmd_cache.diff_nb, ["-p", tmp_path, "1", path2])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    print(result.output.splitlines()[2:])
    assert result.output.splitlines()[1:] == [
        "--- cached pk=1",
        f"+++ other: {path2}",
        "## inserted before nb/cells/0:",
        "+  code cell:",
        "+    source:",
        "+      raise Exception('oopsie!')",
        "",
        "## deleted nb/cells/0:",
        "-  code cell:",
        "-    execution_count: 2",
        "-    source:",
        "-      a=1",
        "-      print(a)",
        "-    outputs:",
        "-      output 0:",
        "-        output_type: stream",
        "-        name: stdout",
        "-        text:",
        "-          1",
        "",
        "",
        "Success!",
    ]


def test_add_nbs_to_project(tmp_path):
    db = JupyterCacheBase(str(tmp_path))
    path = os.path.join(NB_PATH, "basic.ipynb")
    runner = CliRunner()
    result = runner.invoke(cmd_project.add_notebooks, ["-p", tmp_path, path])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output
    assert db.list_project_records()[0].uri == path


def test_remove_nbs_from_project(tmp_path):
    db = JupyterCacheBase(str(tmp_path))
    path = os.path.join(NB_PATH, "basic.ipynb")
    runner = CliRunner()
    result = runner.invoke(cmd_project.add_notebooks, ["-p", tmp_path, path])
    result = runner.invoke(cmd_project.remove_nbs, ["-p", tmp_path, path])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output
    assert db.list_project_records() == []


def test_clear_project(tmp_path):
    db = JupyterCacheBase(str(tmp_path))
    path = os.path.join(NB_PATH, "basic.ipynb")
    runner = CliRunner()
    result = runner.invoke(cmd_project.add_notebooks, ["-p", tmp_path, path])
    result = runner.invoke(cmd_project.clear_nbs, ["-p", tmp_path], input="y")
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert db.list_project_records() == []


def test_list_nbs_in_project(tmp_path):
    db = JupyterCacheBase(str(tmp_path))
    db.cache_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"), check_validity=False
    )
    db.add_nb_to_project(path=os.path.join(NB_PATH, "basic.ipynb"))
    db.add_nb_to_project(path=os.path.join(NB_PATH, "basic_failing.ipynb"))

    runner = CliRunner()
    result = runner.invoke(cmd_project.list_nbs_in_project, ["-p", tmp_path])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output


def test_show_project_record(tmp_path):
    db = JupyterCacheBase(str(tmp_path))
    db.cache_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"), check_validity=False
    )
    db.add_nb_to_project(path=os.path.join(NB_PATH, "basic.ipynb"))

    runner = CliRunner()
    result = runner.invoke(cmd_project.show_project_record, ["-p", tmp_path, "1"])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output


def test_execute(tmp_path):
    db = JupyterCacheBase(str(tmp_path))
    db.add_nb_to_project(path=os.path.join(NB_PATH, "basic.ipynb"))
    runner = CliRunner()
    result = runner.invoke(cmd_exec.execute_nbs, ["-p", tmp_path])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert len(db.list_cache_records()) == 1


def test_project_merge(tmp_path):
    db = JupyterCacheBase(str(tmp_path))
    record = db.add_nb_to_project(path=os.path.join(NB_PATH, "basic_unrun.ipynb"))
    db.cache_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"),
        uri="basic.ipynb",
        check_validity=False,
    )
    runner = CliRunner()
    result = runner.invoke(
        cmd_project.merge_executed,
        ["-p", tmp_path, str(record.pk), str(tmp_path / "output.ipynb")],
    )
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert (tmp_path / "output.ipynb").exists()
