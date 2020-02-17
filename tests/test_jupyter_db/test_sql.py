import json
import os

import nbformat

from jupyter_cache.sql import JupyterCacheSql


NB_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), "notebooks")


def test_add_notebook(tmp_path, data_regression):
    db = JupyterCacheSql(str(tmp_path), echo=False)
    db.add_notebook_file(uri=os.path.join(NB_PATH, "complex_outputs.ipynb"))
    final_db = db.to_dict(drop_columns=("created_at", "updated_at"))
    data_regression.check(final_db)


def test_get_notebook(tmp_path, data_regression):
    db = JupyterCacheSql(str(tmp_path), echo=False)
    uri = os.path.join(NB_PATH, "complex_outputs.ipynb")
    db.add_notebook_file(uri=uri)
    notebook = db.get_notebook(uri=uri)
    data_regression.check(json.loads(nbformat.writes(notebook)))
