# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>

import os, sys, datetime
from pathlib import Path
sys.path.insert(0, os.path.abspath('.'))

from torii_ila import __version__ as torii_ila_version

ROOT_DIR = (Path(__file__).parent).parent


project   = 'Torii ILA'
version   = torii_ila_version
release   = version.split('+')[0]
copyright = f'{datetime.date.today().year}, Aki Van Ness, et. al.'
language  = 'en'

extensions = [
	'sphinx.ext.autodoc',
	'sphinx.ext.doctest',
	'sphinx.ext.githubpages',
	'sphinx.ext.graphviz',
	'sphinx.ext.intersphinx',
	'sphinx.ext.napoleon',
	'sphinx.ext.todo',
	'sphinxcontrib.mermaid',
	'myst_parser',
	'sphinx_autodoc_typehints',
	'sphinx_inline_tabs',
	'sphinxext.opengraph',
]

source_suffix = {
	'.rst': 'restructuredtext',
	'.md': 'markdown',
}

pygments_style              = 'monokai'
autodoc_member_order        = 'bysource'
autodoc_docstring_signature = False
graphviz_output_format      = 'svg'
todo_include_todos          = True

intersphinx_mapping = {
	'python': ('https://docs.python.org/3', None),
	'torii':  ('https://torii.shmdn.link/', None),
	'sol_usb':  ('https://sol.shmdn.link/', None),
	'serial': ('https://pythonhosted.org/pyserial/', None),
}

napoleon_google_docstring              = True
napoleon_numpy_docstring               = True
napoleon_use_ivar                      = True
napoleon_use_admonition_for_notes      = True
napoleon_use_admonition_for_examples   = True
napoleon_use_admonition_for_references = True


myst_heading_anchors = 3

html_baseurl     = 'https://torii-ila.shmdn.link/'
html_theme       = 'furo'
html_copy_source = False

html_theme_options = {
	'top_of_page_buttons': [],
}

html_static_path = [
	'_static'
]

html_css_files = [
	'css/styles.css'
]


ogp_site_url = html_baseurl
ogp_image    = f'{html_baseurl}/_images/og-image.png'

autosectionlabel_prefix_document = True

always_use_bars_union = True

linkcheck_anchors_ignore_for_url = [
	r'^https://web\.libera\.chat/',
]

linkcheck_ignore = [

]
