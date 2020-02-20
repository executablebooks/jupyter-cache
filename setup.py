"""jupyter-cache package setup."""
from importlib import import_module
from setuptools import find_packages, setup

setup(
    name="jupyter-cache",
    version=import_module("jupyter_cache").__version__,
    description=("A defined interface for working with a cache of jupyter notebooks."),
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ExecutableBookProject/jupyter-cache",
    author="Chris Sewell",
    author_email="chrisj_sewell@hotmail.com",
    license="MIT",
    packages=find_packages(),
    entry_points={
        "console_scripts": [],
        # "jupyter_executors": ["default = jupyter_sphinx.executor:run_execution"],
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
    python_requires=">=3.5",
    install_requires=["gitpython", "nbformat", "nbdime", "sqlalchemy"],
    extras_require={
        "code_style": ["flake8<3.8.0,>=3.7.0", "black", "pre-commit==1.17.0"],
        "testing": ["coverage", "pytest>=3.6,<4", "pytest-cov", "pytest-regressions"],
    },
    zip_safe=True,
)
