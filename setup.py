"""jupyter-cache package setup."""
from importlib import import_module
from setuptools import find_packages, setup

setup(
    name="jupyter-cache",
    version=import_module("jupyter_cache").__version__,
    description=("A defined interface for working with a cache of jupyter notebooks."),
    long_description=open("README.md", encoding="utf8").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ExecutableBookProject/jupyter-cache",
    author="Chris Sewell",
    author_email="chrisj_sewell@hotmail.com",
    license="MIT",
    packages=find_packages(),
    entry_points={
        "console_scripts": ["jcache = jupyter_cache.cli.commands.cmd_main:jcache"],
        "jupyter_executors": [
            "basic = jupyter_cache.executors.basic:JupyterExecutorBasic"
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.6",
    # note: nbdime could be made an extra
    install_requires=[
        "attrs",
        "nbformat",
        "nbdime",
        # note: we do not yet pin to higher, since there are reports of issues with 0.3
        # see: https://github.com/jupyter/nbclient/issues/58
        "nbclient>=0.2,<0.5",
        "sqlalchemy~=1.3.12",
    ],
    extras_require={
        "cli": ["click", "click-completion", "click-log", "tabulate", "pyyaml"],
        "code_style": ["flake8<3.8.0,>=3.7.0", "black", "pre-commit==1.17.0"],
        "testing": [
            "coverage",
            "pytest>=3.6,<4",
            "pytest-cov",
            "pytest-regressions",
            "matplotlib",
            "numpy",
            "sympy",
            "pandas",
        ],
        "rtd": ["myst-nb~=0.7", "sphinx-copybutton", "pydata-sphinx-theme"],
    },
    zip_safe=True,
)
