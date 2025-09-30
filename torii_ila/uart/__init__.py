# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>

from argparse import ArgumentParser

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

def _setup_args(parent_parser: ArgumentParser) -> None:
	# If we don't have UART ILA support, bail

	if not ILA_HAS_UART:
		return

	parser = parent_parser.add_argument_group(
		title = 'UART',
		description = 'UART ILA Specific Options'
	)

	parser.add_argument(
		'--baudrate', '-b',
		type = int,
		help = 'The baud rate of the serial link'
	)
