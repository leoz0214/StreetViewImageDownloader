"""DO NOT RUN SPHINX BUILD DIRECTLY - RUN THE build.py module."""
import json

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Street View Image Downloader"
copyright = "2024, Leo Zhang"
author = "Leo Zhang"
release = "1.0.0"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]

# Automation options
extensions = ["autoapi.extension"]
autoapi_dirs = ["_temp"]
autoapi_member_order = "alphabetical"


# JSON file containing the contents to include.
INCLUDE_FILE = "include.json"


with open(INCLUDE_FILE, "r", encoding="utf8") as f:
    INCLUDE = json.load(f)


def skip_unless_included(app, what, name, obj, skip, options) -> bool:
    """Only includes configured contents in the JSON file."""
    parts = name.split(".")
    current = INCLUDE
    for part in parts:
        if part not in current:
            return True
        current = current[part] if isinstance(current, dict) else []
    return False


def setup(sphinx) -> None:
   import build
   sphinx.connect("autoapi-skip-member", skip_unless_included)
