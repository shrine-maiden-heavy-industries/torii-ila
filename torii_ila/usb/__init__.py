# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>

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
