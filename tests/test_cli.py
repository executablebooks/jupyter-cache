import os
from pathlib import Path

from click.testing import CliRunner
import pytest

from jupyter_cache.cache.main import JupyterCacheBase
from jupyter_cache.cli import CacheContext
from jupyter_cache.cli.commands import cmd_cache, cmd_main, cmd_notebook, cmd_project

NB_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), "notebooks")


class Runner(CliRunner):
    def __init__(self, path) -> None:
        super().__init__()
        self._cache_path = path

    def create_cache(self) -> JupyterCacheBase:
        return JupyterCacheBase(str(self._cache_path))

    def invoke(self, *args, **kwargs):
        return super().invoke(*args, **kwargs, obj=CacheContext(self._cache_path))


@pytest.fixture()
def runner(tmp_path):
    return Runner(tmp_path)


def test_base(runner: Runner):
    result = runner.invoke(cmd_main.jcache, "-v")
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "jupyter-cache version" in result.output.strip(), result.output


def test_clear_cache(runner: Runner):
    result = runner.invoke(cmd_project.clear_cache, input="y")
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "Cache cleared!" in result.output.strip(), result.output


def test_list_caches(runner: Runner):
    db = runner.create_cache()
    db.cache_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"),
        uri="basic.ipynb",
        check_validity=False,
    )
    result = runner.invoke(cmd_cache.list_caches, [])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output


def test_list_caches_latest_only(runner: Runner):
    db = runner.create_cache()
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
    result = runner.invoke(cmd_cache.list_caches, [])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert len(result.output.strip().splitlines()) == 4, result.output
    result = runner.invoke(cmd_cache.list_caches, ["--latest-only"])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert len(result.output.strip().splitlines()) == 3, result.output


def test_cache_with_artifact(runner: Runner):
    nb_path = os.path.join(NB_PATH, "basic.ipynb")
    a_path = os.path.join(NB_PATH, "artifact_folder", "artifact.txt")
    result = runner.invoke(
        cmd_cache.cache_nb, ["--no-validate", "-nb", nb_path, a_path]
    )
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output
    result = runner.invoke(cmd_cache.cached_info, ["1"])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "- artifact_folder/artifact.txt" in result.output.strip(), result.output
    result = runner.invoke(
        cmd_cache.cat_artifact, ["1", "artifact_folder/artifact.txt"]
    )
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "An artifact" in result.output.strip(), result.output


def test_cache_nbs(runner: Runner):
    db = runner.create_cache()
    path = os.path.join(NB_PATH, "basic.ipynb")
    result = runner.invoke(cmd_cache.cache_nbs, ["--no-validate", path])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output
    assert db.list_cache_records()[0].uri == path


def test_remove_caches(runner: Runner):
    db = runner.create_cache()
    db.cache_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"),
        uri="basic.ipynb",
        check_validity=False,
    )
    result = runner.invoke(cmd_cache.remove_caches, ["1"])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "Success" in result.output.strip(), result.output
    assert db.list_cache_records() == []


def test_diff_nbs(runner: Runner):
    db = runner.create_cache()
    path = os.path.join(NB_PATH, "basic.ipynb")
    path2 = os.path.join(NB_PATH, "basic_failing.ipynb")
    db.cache_notebook_file(path, check_validity=False)
    # nb_bundle = db.get_cache_bundle(1)
    # nb_bundle.nb.cells[0].source = "# New Title"
    # db.stage_notebook_bundle(nb_bundle)

    result = runner.invoke(cmd_cache.diff_nb, ["1", path2])
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


def test_add_nbs_to_project(runner: Runner):
    db = runner.create_cache()
    path = os.path.join(NB_PATH, "basic.ipynb")
    result = runner.invoke(cmd_notebook.add_notebooks, [path])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output
    assert db.list_project_records()[0].uri == path


def test_remove_nbs_from_project(runner: Runner):
    db = runner.create_cache()
    path = os.path.join(NB_PATH, "basic.ipynb")
    result = runner.invoke(cmd_notebook.add_notebooks, [path])
    result = runner.invoke(cmd_notebook.remove_nbs, [path])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output
    assert db.list_project_records() == []


def test_clear_project(runner: Runner):
    db = runner.create_cache()
    path = os.path.join(NB_PATH, "basic.ipynb")
    result = runner.invoke(cmd_notebook.add_notebooks, [path])
    result = runner.invoke(cmd_notebook.clear_nbs, [], input="y")
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert db.list_project_records() == []


def test_list_nbs_in_project(runner: Runner):
    db = runner.create_cache()
    db.cache_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"), check_validity=False
    )
    db.add_nb_to_project(path=os.path.join(NB_PATH, "basic.ipynb"))
    db.add_nb_to_project(path=os.path.join(NB_PATH, "basic_failing.ipynb"))

    result = runner.invoke(cmd_notebook.list_nbs_in_project, [])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output


def test_show_project_record(runner: Runner):
    db = runner.create_cache()
    db.cache_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"), check_validity=False
    )
    db.add_nb_to_project(path=os.path.join(NB_PATH, "basic.ipynb"))

    result = runner.invoke(cmd_notebook.show_project_record, ["1"])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert "basic.ipynb" in result.output.strip(), result.output


def test_project_execute(runner: Runner):
    db = runner.create_cache()
    db.add_nb_to_project(path=os.path.join(NB_PATH, "basic.ipynb"))
    result = runner.invoke(cmd_project.execute_nbs, [])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert len(db.list_cache_records()) == 1


def test_project_merge(runner: Runner, tmp_path: Path):
    db = runner.create_cache()
    record = db.add_nb_to_project(path=os.path.join(NB_PATH, "basic_unrun.ipynb"))
    db.cache_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"),
        uri="basic.ipynb",
        check_validity=False,
    )
    result = runner.invoke(
        cmd_notebook.merge_executed,
        [str(record.pk), str(tmp_path / "output.ipynb")],
    )
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert (tmp_path / "output.ipynb").exists()


def test_project_invalidate(runner: Runner):
    db = runner.create_cache()
    db.cache_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"), check_validity=False
    )
    db.add_nb_to_project(path=os.path.join(NB_PATH, "basic.ipynb"))

    result = runner.invoke(cmd_notebook.invalidate_nbs, ["1"])
    assert result.exception is None, result.output
    assert result.exit_code == 0, result.output
    assert db.list_project_records()
    assert not db.list_cache_records()
