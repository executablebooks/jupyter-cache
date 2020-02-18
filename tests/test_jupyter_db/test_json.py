import json
import os

import nbformat

from jupyter_cache.json import JupyterCacheJson


NB_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), "notebooks")


def test_add_notebook(tmp_path, data_regression):
    db = JupyterCacheJson(str(tmp_path))
    db.add_notebook_file(uri=os.path.join(NB_PATH, "complex_outputs.ipynb"))
    assert {p.name for p in db.path.glob("*")} == {"1.ipynb", "db.json"}


def test_remove_notebook(tmp_path, data_regression):
    db = JupyterCacheJson(str(tmp_path))
    uri = os.path.join(NB_PATH, "complex_outputs.ipynb")
    db.add_notebook_file(uri=uri)
    db.remove_notebook(uri=uri)
    assert {p.name for p in db.path.glob("*")} == {"db.json"}


def test_get_notebook(tmp_path, data_regression):
    db = JupyterCacheJson(str(tmp_path))
    uri = os.path.join(NB_PATH, "complex_outputs.ipynb")
    db.add_notebook_file(uri=uri)
    notebook = db.get_notebook(uri=uri)
    data_regression.check(json.loads(nbformat.writes(notebook)))
