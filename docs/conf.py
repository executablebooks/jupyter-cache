# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


# -- Project information -----------------------------------------------------

project = "Jupyter Cache"
copyright = "2020, Executable Book Project"
author = "Executable Book Project"

master_doc = "index"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "myst_nb",
    "sphinx.ext.intersphinx",
    "sphinx_copybutton",
    # "sphinx.ext.autodoc",
    # "sphinx.ext.viewcode",
]
jupyter_execute_notebooks = "off"
html_theme_options = {
    "repository_url": "https://github.com/executablebooks/jupyter-cache",
    "use_repository_button": True,
    "use_edit_page_button": True,
    "use_issues_button": True,
    "repository_branch": "master",
    "path_to_docs": "docs",
    "home_page_in_toc": True,
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
    "**/example_nbs/*",
    "**/.jupyter_cache/**/*",
    "**/.ipynb_checkpoints/*",
]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_book_theme"
html_logo = "_static/logo_small.jpg"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
# html_css_files = ["css/custom.css"]


intersphinx_mapping = {"python": ("https://docs.python.org/3.8", None)}
autodoc_member_order = "bysource"

nitpick_ignore = [
    ("py:class", "Any"),
    ("py:class", "Tuple"),
    ("py:class", "ForwardRef"),
    ("py:class", "NoneType"),
]
