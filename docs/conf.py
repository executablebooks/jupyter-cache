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
myst_enable_extensions = ["colon_fence", "deflist"]
nb_execution_mode = "off"
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
html_title = "Jupyter Cache"
html_logo = "_static/logo_wide.svg"
html_favicon = "_static/logo_square.svg"

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


def setup(app):
    import importlib
    import os
    import shutil
    import traceback

    import click
    from click.testing import CliRunner
    from docutils import nodes
    from docutils.parsers.rst import directives
    from sphinx.util.docutils import SphinxDirective

    class JcacheClear(SphinxDirective):
        """A directive to clear the jupyter cache."""

        def run(self):
            path = os.path.join(os.path.dirname(self.env.app.srcdir), ".jupyter_cache")
            if os.path.exists(path):
                shutil.rmtree(path)
            return []

    class JcacheCli(SphinxDirective):
        """A directive to run a CLI command,
        and output a nicely formatted representation of the input command and its output.
        """

        required_arguments = 1  # command
        final_argument_whitespace = False
        has_content = False
        option_spec = {
            "prog": directives.unchanged_required,
            "command": directives.unchanged_required,
            "args": directives.unchanged_required,
            "input": directives.unchanged_required,
            "allow-exception": directives.flag,
        }

        def run(self):
            modpath = self.arguments[0]

            try:
                module_name, attr_name = modpath.split(":", 1)
            except ValueError:
                raise self.error(f'"{modpath}" is not of format "module:command"')

            try:
                module = importlib.import_module(module_name)
            except Exception:
                raise self.error(
                    f"Failed to import '{module_name}': {traceback.format_exc()}"
                )

            if not hasattr(module, attr_name):
                raise self.error(
                    f'Module "{module_name}" has no attribute "{attr_name}"'
                )
            command = getattr(module, attr_name)
            if not isinstance(command, click.Group):
                raise self.error(
                    f'"{modpath}" of type {type(command)}"" is not derived from "click.Group"'
                )

            cmd_string = [self.options.get("prog", "jcache")]
            if command.name != cmd_string[0]:
                cmd_string.append(command.name)
            if "command" in self.options:
                cmd_string.append(self.options["command"])
                command = command.commands[self.options["command"]]

            args = self.options.get("args", "")

            runner = CliRunner()
            root_path = os.path.dirname(self.env.app.srcdir)
            try:
                old_cwd = os.getcwd()
                os.chdir(root_path)
                result = runner.invoke(
                    command, args.split(), input=self.options.get("input", None), env={}
                )
            finally:
                os.chdir(old_cwd)

            if result.exception and "allow-exception" not in self.options:
                raise self.error(
                    f"CLI raised exception: {result.exception}\n---\n{result.output}\n---\n"
                )
            if result.exit_code != 0 and "allow-exception" not in self.options:
                raise self.error(
                    f"CLI non-zero exit code: {result.exit_code}\n---\n{result.output}\n---\n"
                )

            text = f"$ {' '.join(cmd_string)} {args}\n{result.output}"
            text = text.replace(root_path + os.sep, "../")
            node = nodes.literal_block(text, text, language="console")
            return [node]

    app.add_directive("jcache-clear", JcacheClear)
    app.add_directive("jcache-cli", JcacheCli)
