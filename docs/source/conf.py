import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

project = "lifecycle"
copyright = "2026, Romana8192"  # noqa: A001
author = "Romana8192"
release = "1.0.0"
language = "ru"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.graphviz",
    "sphinx.ext.linkcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.doctest",
    "myst_parser",
    "sphinx_design",
]

templates_path = ["_templates"]
exclude_patterns = []

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

suppress_warnings = [
    "toc.not_readable",
    "duplicate_object_description",
]

# Тема
html_theme = "pydata_sphinx_theme"
html_static_path = ["_static"]
html_favicon = "_static/icon.png"
html_show_sourcelink = False

html_theme_options: dict[str, Any] = {
    "navigation_depth": 4,
    "collapse_navigation": False,
    "show_toc_level": 2,
    "header_links_before_dropdown": 4,
    "use_edit_page_button": True,
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/Romana8192/lifecycle",
            "icon": "fab fa-github-square",
        },
    ],
}

html_context = {
    "github_user": "Romana8192",
    "github_repo": "lifecycle",
    "github_version": "main",
    "doc_path": "docs/source",
}

autodoc_member_order = "bysource"
napoleon_include_init_with_doc = True
autodoc_default_options: dict[str, Any] = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "special-members": "__slots__",
    "exclude-members": "__weakref__",
}

doctest_test_doctest_blocks = "default"
doctest_path = [str(Path(__file__).parent / "source")]


def linkcode_resolve(domain: str, info: dict[str, str]) -> str | None:
    if domain != "py":
        return None
    if not info["module"]:
        return None
    module_path = info["module"].replace(".", "/")
    lineno: str | None = info.get("lineno")
    anchor = f"#L{lineno}" if lineno and int(lineno) > 0 else ""
    base_url = "https://github.com/Romana8192/lifecycle/blob/main/src"
    return f"{base_url}/{module_path}.py{anchor}"
