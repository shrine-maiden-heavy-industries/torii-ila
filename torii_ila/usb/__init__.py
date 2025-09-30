# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>

from argparse import ArgumentParser

try:
	from ._impl import USBIntegratedLogicAnalyzerBackhaul, USBIntegratedLogicAnalyzer # noqa: F401

	ILA_HAS_USB = True

	__all__ = (
		'USBIntegratedLogicAnalyzerBackhaul',
		'USBIntegratedLogicAnalyzer',
		'ILA_HAS_USB',
	)

except ImportError:
	ILA_HAS_USB = False

	__all__ = (
		'ILA_HAS_USB',
	)


def _setup_args(parent_parser: ArgumentParser) -> None:
	# If we don't have USB ILA support, bail

	if not ILA_HAS_USB:
		return

	parser = parent_parser.add_argument_group(
		title = 'USB',
		description = 'USB Specific ILA Options'
	)
