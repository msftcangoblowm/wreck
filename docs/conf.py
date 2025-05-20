import importlib.metadata
import re
import sys
from pathlib import Path

from packaging.version import parse
from sphinx_pyproject import SphinxConfig

from wreck.constants import g_app_name as package_name
from wreck.pep518_read import find_project_root

path_docs = Path(__file__).parent
path_package_base = path_docs.parent
sys.path.insert(0, str(path_package_base))  # Needed ??

# Not dynamic. Not using setuptools-scm
release = importlib.metadata.version(package_name)
v = parse(release)
version_short = f"{v.major}.{v.minor}"
version_xyz = f"{v.major}.{v.minor}.{v.micro}"
version_long = str(v)

# @@@ editable
copyright = "2024–2025, Dave Faulkmore"
# The short X.Y.Z version.
version = version_xyz
# The full version, including alpha/beta/rc tags.
release = "0.3.2"
# The date of release, in "monthname day, year" format.
release_date = "February 07, 2025"
# @@@ end

v = parse(release)
version_short = f"{v.major}.{v.minor}"
# version_xyz = f"{v.major}.{v.minor}.{v.micro}"
version_xyz = version

# pyproject.toml search algo. Credit/Source: https://pypi.org/project/black/
srcs = (path_package_base,)
t_root = find_project_root(srcs)

config = SphinxConfig(
    # Path(__file__).parent.parent.joinpath("pyproject.toml"),
    t_root[0] / "pyproject.toml",
    globalns=globals(),
    config_overrides={"version": version_long},
)

# This project is a fork from "Sphinx External ToC"
proj_project = config.name
proj_description = config.description
proj_authors = config.author

slug = re.sub(r"\W+", "-", proj_project.lower())
proj_master_doc = config.get("master_doc")
project = f"{proj_project} {version_xyz}"

###############
# Dynamic
###############
rst_epilog = """
.. |project_name| replace:: {slug}
.. |package-equals-release| replace:: wreck=={release}
""".format(
    release=release, slug=slug
)

html_theme_options = {
    "description": proj_description,
    "show_relbars": True,
    "logo_name": False,
    "logo": "wreck-logo-1.svg",
    "show_powered_by": False,
}

latex_documents = [
    (
        proj_master_doc,
        f"{slug}.tex",
        f"{proj_project} Documentation",
        proj_authors,
        "manual",  # manual, howto, jreport (Japanese)
        True,
    )
]
man_pages = [
    (
        proj_master_doc,
        slug,
        f"{proj_project} Documentation",
        [proj_authors],
        1,
    )
]
texinfo_documents = [
    (
        proj_master_doc,
        slug,
        f"{proj_project} Documentation",
        proj_authors,
        slug,
        proj_description,
        "Miscellaneous",
    )
]

#################
# Static
#################
ADDITIONAL_PREAMBLE = r"""
\DeclareUnicodeCharacter{20BF}{\'k}
"""

latex_elements = {
    "sphinxsetup": "verbatimforcewraps",
    "extraclassoptions": "openany,oneside",
    "preamble": ADDITIONAL_PREAMBLE,
}

html_sidebars = {
    "**": [
        "about.html",
        "searchbox.html",
        "navigation.html",
        "relations.html",
    ],
}

intersphinx_mapping = {
    "python": (  # source https://docs.python.org/3/objects.inv
        "https://docs.python.org/3",
        ("objects-python.inv", None),
    ),
    "python-missing": (
        "https://github.com/python/cpython/blob",
        ("objects-python-missing.inv", "objects-python-missing.txt"),
    ),
    "wreck": (
        "https://wreck.readthedocs.io/en/stable",
        ("objects-wreck.inv", "objects-wreck.txt"),
    ),
    "packaging": (
        "https://packaging.pypa.io/en/stable",
        ("objects-packaging.inv", "objects-packaging.txt"),
    ),
    "black": (
        "https://github.com/psf/black",
        ("objects-black.inv", "objects-black.txt"),
    ),
    "sphinxdocs": (
        "https://www.sphinx-doc.org/en/master",
        ("objects-sphinxdocs.inv", "objects-sphinxdocs.txt"),
    ),
    "gh-setuptools-scm": (
        "https://github.com/pypa/setuptools-scm",
        ("objects-gh-setuptools-scm.inv", "objects-gh-setuptools-scm.txt"),
    ),
    "gh-pytest-dev": (
        "https://github.com/pytest-dev/pytest",
        ("objects-gh-pytest-dev.inv", "objects-gh-pytest-dev.txt"),
    ),
}
intersphinx_disabled_reftypes = ["std:doc"]
autodoc_type_aliases = {
    "TOML_RESULT": "wreck.monkey.pyproject_reading.TOML_RESULT",
    "TOML_LOADER": "wreck.monkey.pyproject_reading.TOML_LOADER",
    "DATUM": "wreck.lock_datum.DATUM",
    "DatumByPkg": "wreck.lock_datum.DatumByPkg",
    "PkgsWithIssues": "wreck.lock_discrepancy.PkgsWithIssues",
}

extlinks = {
    "pypi_org": (  # url to: aiologger
        "https://pypi.org/project/%s",
        "%s",
    ),
}

# spoof user agent to prevent broken links
# curl -A "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:24.0) Gecko/20100101 Firefox/24.0" --head "https://github.com/python/cpython/blob/3.12/Lib/unittest/case.py#L193"
linkcheck_request_headers = {
    "https://github.com/": {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:24.0) Gecko/20100101 Firefox/24.0",
    },
    "https://docs.github.com/": {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:24.0) Gecko/20100101 Firefox/24.0",
    },
}

# Ignore unfixable WARNINGS
# in pyproject.toml --> nitpicky = true
# in conf.py --> nitpicky = True
nitpick_ignore = [
    ("py:class", "ValidatorType"),
    ("py:class", "t.Any"),
    ("py:class", "pathlib._local.Path"),
]

favicons = [
    {"rel": "icon", "href": "icon-wreck-1-200x200-1.svg", "type": "image/svg+xml"},
    {
        "rel": "apple-touch-icon",
        "sizes": "180x180",
        "href": "apple-touch-icon-180x180-1.png",
        "type": "image/png",
    },
]
