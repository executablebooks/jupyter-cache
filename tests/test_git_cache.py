import os

from jupyter_cache.git_cache import JupyterCacheGit


NB_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), "notebooks")


def test_basic_workflow(tmp_path, data_regression):
    db = JupyterCacheGit(str(tmp_path))
    db.stage_notebook_file(path=os.path.join(NB_PATH, "basic.ipynb"), uri="basic.ipynb")
    db.stage_notebook_file(
        path=os.path.join(NB_PATH, "basic.ipynb"), uri="basic2.ipynb"
    )
    assert db.list_staged_notebooks() == {"basic.ipynb", "basic2.ipynb"}
    assert db.list_committed_notebooks() == set()
    db.commit_all()
    assert db.list_staged_notebooks() == set()
    assert db.list_committed_notebooks() == {"basic.ipynb", "basic2.ipynb"}
    db.invalidate_notebook("basic.ipynb")
    db.remove_notebook("basic2.ipynb")
    assert db.list_staged_notebooks() == {"basic.ipynb"}
    assert db.list_committed_notebooks() == set()

    db.commit_all()
    assert db.list_staged_notebooks() == set()
    assert db.list_committed_notebooks() == {"basic.ipynb"}

    nb = db.get_committed_notebook("basic.ipynb")
    nb.cells[1].source = "print('hi')"
    db.stage_notebook_node(nb, "basic.ipynb")
    assert db.list_staged_notebooks() == {"basic.ipynb"}
    assert db.list_committed_notebooks() == {"basic.ipynb"}

    assert db.diff_staged_notebook("basic.ipynb") == [
        {
            "op": "patch",
            "key": "cells",
            "diff": [
                {
                    "op": "addrange",
                    "key": 1,
                    "valuelist": [
                        {
                            "cell_type": "code",
                            "execution_count": 2,
                            "metadata": {},
                            "outputs": [
                                {
                                    "name": "stdout",
                                    "output_type": "stream",
                                    "text": "1\n",
                                }
                            ],
                            "source": "print('hi')",
                        }
                    ],
                },
                {"op": "removerange", "key": 1, "length": 1},
            ],
        }
    ]
