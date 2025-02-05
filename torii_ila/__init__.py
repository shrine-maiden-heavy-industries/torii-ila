# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>

try:
	from importlib import metadata
	__version__ = metadata.version(__package__)
except ImportError: # :nocov:
	__version__ = 'unknown'

from .ila import IntegratedLogicAnalyzer, StreamILA

try:
	from .uart import UARTIntegratedLogicAnalyzer, UARTIntegratedLogicAnalyzerBackhaul
	_ILA_UART_IMPORTS = ('UARTIntegratedLogicAnalyzer', 'UARTIntegratedLogicAnalyzerBackhaul',)
	ILA_HAS_UART_SUPPORT = True
except ImportError:
	_ILA_UART_IMPORTS = tuple()
	ILA_HAS_UART_SUPPORT = False

try:
	from .usb import USBIntegratedLogicAnalyzer, USBIntegratedLogicAnalyzerBackhaul
	_ILA_USB_IMPORTS = ('USBIntegratedLogicAnalyzer', 'USBIntegratedLogicAnalyzerBackhaul',)
	ILA_HAS_USB_SUPPORT = True
except ImportError:
	_ILA_USB_IMPORTS = tuple()
	ILA_HAS_USB_SUPPORT = False

__all__ = (
	'IntegratedLogicAnalyzer', 'StreamILA',
	*_ILA_UART_IMPORTS,
	*_ILA_USB_IMPORTS,
)
