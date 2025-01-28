# SPDX-License-Identifier: BSD-3-Clause

try:
	from importlib import metadata
	__version__ = metadata.version(__package__)
except ImportError: # :nocov:
	__version__ = 'unknown'

from .ila import IntegratedLogicAnalyzer, StreamILA

__all__ = (
	'IntegratedLogicAnalyzer', 'StreamILA',
)
