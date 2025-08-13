# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>

try:
	from importlib import metadata
	__version__ = metadata.version(__package__)
except ImportError: # :nocov:
	__version__ = 'unknown'

from .ila  import IntegratedLogicAnalyzer, StreamILA
from .uart import UARTIntegratedLogicAnalyzer, UARTIntegratedLogicAnalyzerBackhaul
from .usb  import USBIntegratedLogicAnalyzer, USBIntegratedLogicAnalyzerBackhaul

__all__ = (
	'IntegratedLogicAnalyzer',
	'StreamILA',
	'UARTIntegratedLogicAnalyzer',
	'UARTIntegratedLogicAnalyzerBackhaul',
	'USBIntegratedLogicAnalyzer',
	'USBIntegratedLogicAnalyzerBackhaul',
)
