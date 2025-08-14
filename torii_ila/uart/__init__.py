# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>

try:
	from ._impl import UARTILACommand, UARTIntegratedLogicAnalyzerBackhaul, UARTIntegratedLogicAnalyzer # noqa: F401

	ILA_HAS_UART = True

	__all__ = (
		'UARTILACommand',
		'UARTIntegratedLogicAnalyzerBackhaul',
		'UARTIntegratedLogicAnalyzer',
		'ILA_HAS_UART',
	)

except ImportError:
	ILA_HAS_UART = False

	__all__ = (
		'ILA_HAS_UART',
	)
