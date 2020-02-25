import os
from textwrap import dedent

import nbformat as nbf
import pytest

from jupyter_cache.cache import JupyterCacheBase
from jupyter_cache.base import NbValidityError


NB_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), "notebooks")


def test_basic_workflow(tmp_path):
    cache = JupyterCacheBase(str(tmp_path))
    with pytest.raises(NbValidityError):
        cache.commit_notebook_file(path=os.path.join(NB_PATH, "basic.ipynb"))
    cache.commit_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"),
        uri="basic.ipynb",
        check_validity=False,
    )
    assert cache.list_commit_records()[0].uri == "basic.ipynb"
    pk = cache.match_commit_file(path=os.path.join(NB_PATH, "basic.ipynb")).pk
    nb_bundle = cache.get_commit_bundle(pk)
    assert nb_bundle.nb.metadata["kernelspec"] == {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    assert set(nb_bundle.commit.keys()) == {
        "pk",
        "hashkey",
        "uri",
        "data",
        "created",
        "accessed",
        "description",
    }
    # assert cache.get_commit_codecell(pk, 0).source == "a=1\nprint(a)"

    path = os.path.join(NB_PATH, "basic_failing.ipynb")
    diff = cache.diff_nbfile_with_commit(pk, path, as_str=True, use_color=False)
    assert diff == dedent(
        f"""\
        nbdiff
        --- committed pk=1
        +++ other: {path}
        ## inserted before nb/cells/0:
        +  code cell:
        +    source:
        +      raise Exception('oopie')

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
    cache.remove_commit(pk)
    assert cache.list_commit_records() == []

    cache.commit_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"),
        uri="basic.ipynb",
        check_validity=False,
    )
    cache.stage_notebook_file(os.path.join(NB_PATH, "basic.ipynb"))
    assert [r.pk for r in cache.list_staged_records()] == [1]
    assert [r.pk for r in cache.list_nbs_to_exec()] == []

    cache.stage_notebook_file(os.path.join(NB_PATH, "basic_failing.ipynb"))
    assert [r.pk for r in cache.list_staged_records()] == [1, 2]
    assert [r.pk for r in cache.list_nbs_to_exec()] == [2]

    bundle = cache.get_staged_notebook(os.path.join(NB_PATH, "basic_failing.ipynb"))
    assert bundle.nb.metadata

    cache.clear_cache()
    assert cache.list_commit_records() == []


def test_merge_match_into_notebook(tmp_path):
    cache = JupyterCacheBase(str(tmp_path))
    cache.commit_notebook_file(
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
        cache.commit_notebook_file(
            path=os.path.join(NB_PATH, "basic.ipynb"),
            uri="basic.ipynb",
            artifacts=(os.path.join(NB_PATH),),
            check_validity=False,
        )
    cache.commit_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"),
        uri="basic.ipynb",
        artifacts=(os.path.join(NB_PATH, "artifact_folder", "artifact.txt"),),
        check_validity=False,
    )
    hashkey = cache.get_commit_record(1).hashkey
    assert {
        str(p.relative_to(tmp_path)) for p in tmp_path.glob("**/*") if p.is_file()
    } == {
        "global.db",
        f"executed/{hashkey}/base.ipynb",
        f"executed/{hashkey}/artifacts/artifact_folder/artifact.txt",
    }

    bundle = cache.get_commit_bundle(1)
    assert {str(p) for p in bundle.artifacts.relative_paths} == {
        "artifact_folder/artifact.txt"
    }

    text = list(h.read().decode() for r, h in bundle.artifacts)[0]
    assert text.rstrip() == "An artifact"

    with cache.commit_artefacts_temppath(1) as path:
        assert path.joinpath("artifact_folder").exists()


def test_execution(tmp_path):
    from jupyter_cache.executors import load_executor

    db = JupyterCacheBase(str(tmp_path))
    db.stage_notebook_file(path=os.path.join(NB_PATH, "basic_unrun.ipynb"))
    db.stage_notebook_file(path=os.path.join(NB_PATH, "basic_failing.ipynb"))
    db.stage_notebook_file(path=os.path.join(NB_PATH, "external_output.ipynb"))
    executor = load_executor("basic", db)
    assert executor.run() == [
        os.path.join(NB_PATH, "basic_unrun.ipynb"),
        os.path.join(NB_PATH, "external_output.ipynb"),
    ]
    assert len(db.list_commit_records()) == 2
    assert db.get_commit_bundle(1).nb.cells[0] == {
        "cell_type": "code",
        "execution_count": 1,
        "metadata": {},
        "outputs": [{"name": "stdout", "output_type": "stream", "text": "1\n"}],
        "source": "a=1\nprint(a)",
    }
    with db.commit_artefacts_temppath(2) as path:
        paths = [str(p.relative_to(path)) for p in path.glob("**/*") if p.is_file()]
        assert paths == ["artifact.txt"]
        assert path.joinpath("artifact.txt").read_text() == "hi"
