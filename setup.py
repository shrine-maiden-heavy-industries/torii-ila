#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>

from setuptools import setup, find_packages
from pathlib    import Path

REPO_ROOT   = Path(__file__).parent
README_FILE = (REPO_ROOT / 'README.md')

def scm_version():
	def local_scheme(version):
		if version.tag and not version.distance:
			return version.format_with('')
		else:
			return version.format_choice('+{node}', '+{node}.dirty')
	return {
		'relative_to'   : __file__,
		'version_scheme': 'guess-next-dev',
		'local_scheme'  : local_scheme
	}

DOCS_URL = 'https://torii-ila.shmdn.link/'

setup(
	name             = 'torii-ila',
	use_scm_version  = scm_version(),
	author           = 'Aki Van Ness',
	author_email     = 'aki@lethalbit.net',
	description      = 'Integrated Logic Analyzer module for Torii',
	license          = 'BSD-3-Clause',
	python_requires  = '~=3.11',
	zip_safe         = True,
	url              = DOCS_URL,

	long_description = README_FILE.read_text(),
	long_description_content_type = 'text/markdown',

	setup_requires   = [
		'wheel',
		'setuptools',
		'setuptools_scm'
	],

	install_requires = [
		'torii>=0.7.1,<1.0',
		'pyvcd', # NOTE(aki): This is constrained by the same dep in Torii
	],

	extras_require   = {
		'dev': [
			'nox',
		],

		# USB Backhaul
		'usb': [
			'sol-usb>=0.4.1,<1.0',
			'libusb1>=1.8.1',
			'pyusb',
		],

		# UART Backhaul
		'serial': [
			'pyserial',
		],

		'examples': [
			# Board definition files
			'torii-boards>=0.6.1,<1.0',
			# USB ILA Example
			'sol-usb>=0.4.1,<1.0',
			'libusb1>=1.8.1',
			'pyusb',
			# UART ILA Example
			'pyserial',
		]
	},

	packages = find_packages(
		where   = '.',
		exclude = (
			'tests',
			'tests.*',
			'contrib',
			'contrib.*',
			'examples',
			'examples.*',
		)
	),
	package_data  = {
		'torii_ila': [
			'py.typed'
		],
	},

	classifiers = [
		'Development Status :: 4 - Beta',

		'Intended Audience :: Developers',
		'Intended Audience :: Information Technology',
		'Intended Audience :: Science/Research',

		'License :: OSI Approved :: BSD License',

		'Operating System :: MacOS :: MacOS X',
		'Operating System :: Microsoft :: Windows',
		'Operating System :: POSIX :: Linux',

		'Programming Language :: Python :: 3.11',
		'Programming Language :: Python :: 3.12',
		'Programming Language :: Python :: 3.13',

		'Topic :: Scientific/Engineering',
		'Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)',
		'Topic :: Software Development',
		'Topic :: Software Development :: Embedded Systems',
		'Topic :: Software Development :: Libraries',

		'Typing :: Typed',
	],

	project_urls     = {
		'Documentation': DOCS_URL,
		'Source Code'  : 'https://github.com/shrine-maiden-heavy-industries/torii-ila',
		'Bug Tracker'  : 'https://github.com/shrine-maiden-heavy-industries/torii-ila/issues',
	},
)
