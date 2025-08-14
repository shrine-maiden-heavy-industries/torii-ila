# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>

try:
	from importlib import metadata
	__version__ = metadata.version(__package__)
except ImportError: # :nocov:
	__version__ = 'unknown'

from .uart import ILA_HAS_UART
from .usb  import ILA_HAS_USB

__all__ = (
	'ILA_HAS_UART',
	'ILA_HAS_USB',
)
