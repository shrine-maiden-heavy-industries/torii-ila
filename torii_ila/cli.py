# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>

from argparse  import ArgumentParser, ArgumentDefaultsHelpFormatter
from pathlib   import Path

from torii.hdl import Elaboratable

from .uart     	import _setup_args as _setup_uart_args
from .usb      import _setup_args as _setup_usb_args

def _setup_common(parent_parser: ArgumentParser) -> None:
	parser = parent_parser.add_argument_group(
		title = 'Common',
		description = 'Common ILA Options'
	)

	parser.add_argument(
		'--sample-depth', '-d',
		metavar = 'SAMPLE_DEPTH',
		type    = int,
		default = 128,
		help    = 'The number of samples to store in the ILA buffer',
	)

	parser.add_argument(
		'--sample-width', '-w',
		metavar  = 'SAMPLE_WIDTH',
		type     = int,
		required = True,
		help     = 'The width of each sample'
	)

	parser.add_argument(
		'--sampling-domain', '-D',
		metavar = 'SAMPLE_DOMAIN',
		type    = str,
		default = 'sync',
		help    = 'The name of the clock domain the ILA sampling will be done on'
	)

	parser.add_argument(
		'--sample-rate', '-r',
		metavar  = 'SAMPLE_RATE',
		type     = int,
		required = True,
		help     = 'The speed of the ILA sampling domain in MHz'
	)

	parser.add_argument(
		'--io-domain', '-i',
		metavar = 'IO_DOMAIN',
		type    = str,
		default = 'sync',
		help    = 'The name of the clock domain the ILA samples will be output on'
	)

	parent_parser.add_argument(
		'--io-speed', '-I',
		metavar  = 'IO_SPEED',
		type     = int,
		required = True,
		help     = 'The speed of the ILA IO domain in MHz'
	)

	parser.add_argument(
		'--output', '-o',
		metavar = 'OUTPUT',
		type    = Path,
		default = (Path.cwd() / 'ila.v').relative_to(Path.cwd()),
		help    = 'The output file'
	)

def main() -> int:

	parser = ArgumentParser(
		prog = 'torii-ila',
		description = 'CLI interface for the Torii ILA',
		formatter_class = ArgumentDefaultsHelpFormatter
	)

	_setup_common(parser)
	_setup_uart_args(parser)
	_setup_usb_args(parser)

	args = parser.parse_args()

	return 0
