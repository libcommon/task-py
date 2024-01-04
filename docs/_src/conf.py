# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.

from pathlib import Path
import sys


modules_root_path = (Path(__file__)
    .resolve()
    .parents[2]
    .joinpath("src"))
sys.path.insert(0, str(modules_root_path))


# -- Project information -----------------------------------------------------

project = "task-py"
copyright = "2023, Libcommon"
author = "Libcommon"

# The short X.Y.Z version
version = "0.3.1"

# The full version, including alpha/beta/rc tags
release = version


# -- General configuration ---------------------------------------------------

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "Thumbs.db",
    ".DS_Store",
]

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named "sphinx.ext.*") or your custom
# ones.
extensions = [
    "myst_parser",
    "sphinx_copybutton",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.todo",
]

# Root/master document
master_doc = "index"

# Add any paths that contain templates here, relative to this directory.
templates_path = [
    "_templates",
]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_material"
html_title = project
html_short_title = html_title

# Theme options
# See: https://bashtage.github.io/sphinx-material/customization.html#customization
html_theme_options = {

    # Specify a base_url used to generate sitemap.xml. If not
    # specified, then no sitemap will be built.
    "base_url": "",

    # Set the color and the accent color
    "color_primary": "",
    "color_accent": "",

    # Set the repo location to get a badge with stats
    "repo_url": "https://github.com/libcommon/task-py",
    "repo_name": project,

    # If True, minify CSS files in output directory    
    "css_minify": True,    
    # Visible levels of the global TOC; -1 means unlimited                                    
    "globaltoc_depth": 3,                                    
    # If False, expand all TOC entries                                    
    "globaltoc_collapse": True,                                    
    # If True, show hidden TOC entries                                    
    "globaltoc_includehidden": False,                                    
    # If True, minify HTML after generation                                    
    "html_minify": True,                                    
    # If True, show version dropdown                                    
    "version_dropdown": True,
    # Path to versions JSON file relative to site root
    "version_json": "../versions.json",
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = [
    "_static/",
]

# Override default to include global TOC                                                           
html_sidebars = {                                  
    "**": ["logo-text.html", "globaltoc.html", "localtoc.html", "searchbox.html"]                                     
}


# -- Extension configuration -------------------------------------------------

# -- Options for copybutton extension ---------------------------------------
# See: https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html

autodoc_default_options = {
    "inherited-members": False,
    "members": True,
    "show-inheritance": True,
    "private-members": "_preamble, _perform_task, _postamble, _result_cls, _task_cls, _gen_task",
}

autodoc_type_aliases = {
    "CliParserConfig": "lc_task.cli.CliParserConfig",
    "StatePropagationSource": "lc_task.task.StatePropagationSource",
}

# -- Options for copybutton extension ---------------------------------------
# See: https://sphinx-copybutton.readthedocs.io/en/latest/

copybutton_here_doc_delimiter = "EOF"
copybutton_line_continuation_character = "\\"
copybutton_prompt_text = "> "


# -- Options for intersphinx extension ---------------------------------------
# See: https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}


# -- Options for MyST extension ----------------------------------------------
# See: https://myst-parser.readthedocs.io/en/latest/sphinx/reference.html

myst_heading_anchors = 3

myst_number_code_blocks = [
    "python3",
]


# -- Options for napoleon extension ----------------------------------------------

# Use Google-style docstrings
napoleon_google_docstring = True
# Use the admonition directive (.. admonition::) for Example(s) sections
napoleon_use_admonition_for_examples = True
# Use the admonition directive (.. admonition::) for Note(s) section
napoleon_use_admonition_for_notes = True
# Use type annotations for attributes in class body
napoleon_attr_annotations = True


# -- Options for todo extension ----------------------------------------------
# See: https://www.sphinx-doc.org/en/master/usage/extensions/todo.html

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True
