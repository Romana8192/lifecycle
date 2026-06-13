import sys
import warnings
from pathlib import Path

# Подавляем предупреждения Sphinx о дублировании описаний объектов
warnings.filterwarnings("ignore", message="повторное описание объекта", module="sphinx")
warnings.filterwarnings("ignore", category=UserWarning, module="sphinx.ext.autodoc")

root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root / "src"))

project = "lifecycle"
copyright = "2026, Romana8192"
author = "Romana8192"
release = "1.0.0"
language = "ru"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.graphviz",
    "sphinx.ext.linkcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.doctest",
]

templates_path = ["_templates"]
exclude_patterns = []

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

suppress_warnings = [
    "toc.not_readable",
    "duplicate_object_description",
    "autodoc.duplicate_object_description",
]

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Отключаем модульный индекс (py-modindex), чтобы избежать предупреждений о дублировании
html_use_modindex = False

html_theme_options = {
    "navigation_depth": 4,
    "includehidden": False,
    "prev_next_buttons_location": "both",
    "style_external_links": True,
    "collapse_navigation": False,
    "sticky_navigation": True,
}

autodoc_member_order = "bysource"
napoleon_include_init_with_doc = True
autodoc_default_options = {
    "members": True,
    "undoc-members": True,
    "show-inheritance": True,
    "special-members": "__slots__",
    "exclude-members": "__weakref__",
}

doctest_test_doctest_blocks = "default"
doctest_path = [str(Path(__file__).parent / "source")]


def linkcode_resolve(domain, info) -> str | None:
    if domain != "py":
        return None
    if not info["module"]:
        return None
    module_path = info["module"].replace(".", "/")
    base_url = "https://github.com/Romana8192/lifecycle/blob/main/src"
    return f"{base_url}/{module_path}.py"
