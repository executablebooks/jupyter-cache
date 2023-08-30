import os
import re
import shutil
from textwrap import dedent

import nbformat as nbf
import pytest

from jupyter_cache import __version__
from jupyter_cache.base import NbValidityError
from jupyter_cache.cache.main import JupyterCacheBase

NB_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), "notebooks")
ANSI_REGEX = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def test_get_version(tmp_path):
    cache = JupyterCacheBase(str(tmp_path))
    cache.db
    assert cache.get_version() == __version__


def test_basic_workflow(tmp_path):
    cache = JupyterCacheBase(str(tmp_path))
    with pytest.raises(NbValidityError):
        cache.cache_notebook_file(path=os.path.join(NB_PATH, "basic.ipynb"))
    cache.cache_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"),
        uri="basic.ipynb",
        check_validity=False,
    )
    assert cache.list_cache_records()[0].uri == "basic.ipynb"
    pk = cache.match_cache_file(path=os.path.join(NB_PATH, "basic.ipynb")).pk
    nb_bundle = cache.get_cache_bundle(pk)
    assert nb_bundle.nb.metadata["kernelspec"] == {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    assert set(nb_bundle.record.to_dict().keys()) == {
        "pk",
        "hashkey",
        "uri",
        "data",
        "created",
        "accessed",
        "description",
    }
    # assert cache.get_cache_codecell(pk, 0).source == "a=1\nprint(a)"

    path = os.path.join(NB_PATH, "basic_failing.ipynb")
    diff = cache.diff_nbfile_with_cache(pk, path, as_str=True, use_color=False)
    assert diff == dedent(
        f"""\
        nbdiff
        --- cached pk=1
        +++ other: {path}
        ## inserted before nb/cells/0:
        +  code cell:
        +    source:
        +      raise Exception('oopsie!')

        ## deleted nb/cells/0:
        -  code cell:
        -    execution_count: 2
        -    source:
        -      a=1
        -      print(a)
        -    outputs:
        -      output 0:
        -        output_type: stream
        -        name: stdout
        -        text:
        -          1

        """
    )
    cache.remove_cache(pk)
    assert cache.list_cache_records() == []

    cache.cache_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"),
        uri="basic.ipynb",
        check_validity=False,
    )
    with pytest.raises(ValueError):
        cache.add_nb_to_project(os.path.join(NB_PATH, "basic.ipynb"), assets=[""])
    cache.add_nb_to_project(
        os.path.join(NB_PATH, "basic.ipynb"),
        assets=[os.path.join(NB_PATH, "basic.ipynb")],
    )
    assert [r.pk for r in cache.list_project_records()] == [1]
    assert [r.pk for r in cache.list_unexecuted()] == []

    cache.add_nb_to_project(os.path.join(NB_PATH, "basic_failing.ipynb"))
    assert [r.pk for r in cache.list_project_records()] == [1, 2]
    assert [r.pk for r in cache.list_unexecuted()] == [2]

    bundle = cache.get_project_notebook(os.path.join(NB_PATH, "basic_failing.ipynb"))
    assert bundle.nb.metadata

    cache.clear_cache()
    assert cache.list_cache_records() == []


def test_v4_2_to_v4_5(tmp_path):
    """Test that caching a v4.2 notebook can be recovered,
    if the notebook is updated to v4.5 (adding cell ids).
    """
    cache = JupyterCacheBase(str(tmp_path))
    cache_record = cache.cache_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"),
        uri="basic.ipynb",
        check_validity=False,
    )
    (pk, nb) = cache.merge_match_into_notebook(
        nbf.read(os.path.join(NB_PATH, "basic_v4-5.ipynb"), nbf.NO_CONVERT)
    )
    assert cache_record.pk == pk
    assert nb.nbformat_minor == 5, nb
    assert "id" in nb.cells[1], nb


def test_v4_5_to_v4_2(tmp_path):
    """Test that caching a v4.5 notebook can be recovered,
    if the notebook is downgraded to v4.2 (removing cell ids).
    """
    cache = JupyterCacheBase(str(tmp_path))
    cache_record = cache.cache_notebook_file(
        path=os.path.join(NB_PATH, "basic_v4-5.ipynb"),
        uri="basic_v4-5.ipynb",
        check_validity=False,
    )
    (pk, nb) = cache.merge_match_into_notebook(
        nbf.read(os.path.join(NB_PATH, "basic.ipynb"), nbf.NO_CONVERT)
    )
    assert cache_record.pk == pk
    assert nb.nbformat_minor == 2, nb
    assert "id" not in nb.cells[1], nb


def test_merge_match_into_notebook(tmp_path):
    cache = JupyterCacheBase(str(tmp_path))
    cache.cache_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"), check_validity=False
    )
    nb = nbf.read(os.path.join(NB_PATH, "basic_unrun.ipynb"), 4)
    pk, merged = cache.merge_match_into_notebook(nb)
    assert merged.cells[1] == {
        "cell_type": "code",
        "execution_count": 2,
        "metadata": {},
        "outputs": [{"name": "stdout", "output_type": "stream", "text": "1\n"}],
        "source": "a=1\nprint(a)",
    }


def test_artifacts(tmp_path):
    cache = JupyterCacheBase(str(tmp_path))
    with pytest.raises(IOError):
        cache.cache_notebook_file(
            path=os.path.join(NB_PATH, "basic.ipynb"),
            uri="basic.ipynb",
            artifacts=(os.path.join(NB_PATH),),
            check_validity=False,
        )
    cache.cache_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"),
        uri="basic.ipynb",
        artifacts=(os.path.join(NB_PATH, "artifact_folder", "artifact.txt"),),
        check_validity=False,
    )
    hashkey = cache.get_cache_record(1).hashkey
    assert {
        str(p.relative_to(tmp_path)) for p in tmp_path.glob("**/*") if p.is_file()
    } == {
        "global.db",
        "__version__.txt",
        f"executed/{hashkey}/base.ipynb",
        f"executed/{hashkey}/artifacts/artifact_folder/artifact.txt",
    }

    bundle = cache.get_cache_bundle(1)
    assert {str(p) for p in bundle.artifacts.relative_paths} == {
        "artifact_folder/artifact.txt"
    }

    text = list(h.read().decode() for r, h in bundle.artifacts)[0]
    assert text.rstrip() == "An artifact"

    with cache.cache_artefacts_temppath(1) as path:
        assert path.joinpath("artifact_folder").exists()


@pytest.mark.parametrize(
    "executor_key", ["local-serial", "temp-serial", "local-parallel", "temp-parallel"]
)
def test_execution(tmp_path, executor_key):
    from jupyter_cache.executors import load_executor

    db = JupyterCacheBase(str(tmp_path / "cache"))
    temp_nb_path = tmp_path / "notebooks"
    shutil.copytree(NB_PATH, temp_nb_path)
    db.add_nb_to_project(path=os.path.join(temp_nb_path, "basic_unrun.ipynb"))
    db.add_nb_to_project(path=os.path.join(temp_nb_path, "basic_failing.ipynb"))
    db.add_nb_to_project(
        path=os.path.join(temp_nb_path, "external_output.ipynb"),
        assets=(os.path.join(temp_nb_path, "basic.ipynb"),),
    )
    executor = load_executor(executor_key, db)
    result = executor.run_and_cache()
    # print(result)
    json_result = result.as_json()
    json_result["succeeded"] = list(sorted(json_result.get("succeeded", [])))
    assert json_result == {
        "succeeded": [
            os.path.join(temp_nb_path, "basic_unrun.ipynb"),
            os.path.join(temp_nb_path, "external_output.ipynb"),
        ],
        "excepted": [os.path.join(temp_nb_path, "basic_failing.ipynb")],
        "errored": [],
    }
    assert len(db.list_cache_records()) == 2
    cache_record = db.get_cached_project_nb(1)
    bundle = db.get_cache_bundle(cache_record.pk)
    assert bundle.nb.cells[0] == {
        "cell_type": "code",
        "execution_count": 1,
        "metadata": {},
        "outputs": [{"name": "stdout", "output_type": "stream", "text": "1\n"}],
        "source": "a=1\nprint(a)",
    }
    assert "execution_seconds" in bundle.record.data

    # TODO artifacts
    # with db.cache_artefacts_temppath(2) as path:
    #     paths = [str(p.relative_to(path)) for p in path.glob("**/*") if p.is_file()]
    #     assert paths == ["artifact.txt"]
    #     assert path.joinpath("artifact.txt").read_text(encoding="utf8") == "hi"

    project_record = db.get_project_record(2)
    assert project_record.traceback is not None
    assert "Exception: oopsie!" in ANSI_REGEX.sub("", project_record.traceback)


def test_execution_jupytext(tmp_path):
    """Test execution with the jupytext reader."""
    from jupyter_cache.executors import load_executor

    db = JupyterCacheBase(str(tmp_path / "cache"))
    temp_nb_path = tmp_path / "notebooks"
    shutil.copytree(NB_PATH, temp_nb_path)
    db.add_nb_to_project(
        path=os.path.join(temp_nb_path, "basic.md"),
        read_data={"name": "jupytext", "type": "plugin"},
    )
    executor = load_executor("local-serial", db)
    result = executor.run_and_cache()
    print(result)
    assert result.as_json() == {
        "succeeded": [
            os.path.join(temp_nb_path, "basic.md"),
        ],
        "excepted": [],
        "errored": [],
    }
    assert len(db.list_cache_records()) == 1


def test_execution_timeout_config(tmp_path):
    """tests the timeout value passed to the executor"""
    from jupyter_cache.executors import load_executor

    db = JupyterCacheBase(str(tmp_path))
    db.add_nb_to_project(path=os.path.join(NB_PATH, "sleep_2.ipynb"))
    executor = load_executor("local-serial", db)
    result = executor.run_and_cache(timeout=10)
    assert result.as_json() == {
        "succeeded": [os.path.join(NB_PATH, "sleep_2.ipynb")],
        "excepted": [],
        "errored": [],
    }
    db.clear_cache()

    db.add_nb_to_project(path=os.path.join(NB_PATH, "sleep_2.ipynb"))
    executor = load_executor("local-serial", db)
    result = executor.run_and_cache(timeout=1)
    assert result.as_json() == {
        "succeeded": [],
        "excepted": [os.path.join(NB_PATH, "sleep_2.ipynb")],
        "errored": [],
    }


def test_execution_timeout_metadata(tmp_path):
    """tests the timeout metadata key in notebooks"""
    from jupyter_cache.executors import load_executor

    db = JupyterCacheBase(str(tmp_path))
    db.add_nb_to_project(path=os.path.join(NB_PATH, "sleep_2_timeout_1.ipynb"))
    executor = load_executor("local-serial", db)
    result = executor.run_and_cache()
    assert result.as_json() == {
        "succeeded": [],
        "excepted": [os.path.join(NB_PATH, "sleep_2_timeout_1.ipynb")],
        "errored": [],
    }


def test_execution_allow_errors_config(tmp_path):
    """tests the timeout value passed to the executor"""
    from jupyter_cache.executors import load_executor

    db = JupyterCacheBase(str(tmp_path))
    db.add_nb_to_project(path=os.path.join(NB_PATH, "basic_failing.ipynb"))
    executor = load_executor("local-serial", db)
    result = executor.run_and_cache(allow_errors=True)
    assert result.as_json() == {
        "succeeded": [os.path.join(NB_PATH, "basic_failing.ipynb")],
        "excepted": [],
        "errored": [],
    }


def test_run_in_temp_false(tmp_path):
    """tests the timeout value passed to the executor"""
    from jupyter_cache.executors import load_executor

    db = JupyterCacheBase(str(tmp_path))
    db.add_nb_to_project(path=os.path.join(NB_PATH, "basic.ipynb"))
    executor = load_executor("temp-serial", db)
    result = executor.run_and_cache()
    assert result.as_json() == {
        "succeeded": [os.path.join(NB_PATH, "basic.ipynb")],
        "excepted": [],
        "errored": [],
    }
