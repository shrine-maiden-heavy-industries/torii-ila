#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>
#
# This example show the use of the USB ILA with iCEBreaker Bitsy for 1BitSquared:
# (https://1bitsquared.com/products/icebreaker-bitsy)
#
# NOTE:
# When connecting the iCEBreaker Bitsy, ensure to hold the bootloader button down
# so it starts up in DFU mode so this script can automatically upload the bitstream to
# the device.
#
# To run the example, simply run `python bitsy_usb_ila.py` It will build the example
# gateware with an ILA, open the USB backhaul connection, and program the iCEBreaker Bitsy
# with the gateware. It will printout the samples to the terminal and also should produce
# a VCD file with the same data.


import sys
from pathlib                               import Path
from enum                                  import Enum
from subprocess                            import CalledProcessError

from torii.hdl                             import (
	ClockDomain, ClockSignal, Const, Elaboratable, Instance, Module, Signal, ResetSignal
)
from torii.build                           import Platform

from torii_boards.lattice.icebreaker_bitsy import ICEBreakerBitsyPlatform

try:
	from torii_ila import USBIntegratedLogicAnalyzer
except ImportError:
	torii_ila_path = Path(__file__).resolve().parent

	if (torii_ila_path.parent / 'torii_ila').is_dir():
		sys.path.insert(0, str(torii_ila_path.parent))

	from torii_ila import USBIntegratedLogicAnalyzer


class PLL(Elaboratable):
	''' 12MHz -> 48MHz PLL '''
	def __init__(self) -> None:
		self.locked = Signal()

	def elaborate(self, platform: Platform) -> Module:
		m = Module()

		m.domains.sync    = ClockDomain()
		m.domains.usb     = ClockDomain()
		m.domains.usb_io  = ClockDomain()

		platform.lookup(platform.default_clk).attrs['GLOBAL'] = False

		pll_clk = Signal()
		usb_clk = Signal()

		m.submodules.pll = Instance(
			'SB_PLL40_PAD',
			i_PACKAGEPIN    = platform.request(platform.default_clk, dir = 'i'),
			i_RESETB        = Const(1),
			i_BYPASS        = Const(0),

			o_PLLOUTCORE    = pll_clk,
			o_LOCK          = self.locked,

			p_FEEDBACK_PATH = 'SIMPLE',
			p_PLLOUT_SELECT = 'GENCLK',
			p_DIVR          = 0,
			p_DIVF          = 63,
			p_DIVQ          = 4,
			p_FILTER_RANGE  = 1
		)

		platform.add_clock_constraint(pll_clk, 48e6)
		platform.add_clock_constraint(usb_clk, 12e6)

		clk_div = Signal(range(4))
		m.d.usb_io += [ clk_div.inc(), ]

		m.d.comb += [
			usb_clk.eq(clk_div[1]),

			ClockSignal('sync').eq(pll_clk),
			ClockSignal('usb_io').eq(pll_clk),
			ClockSignal('usb').eq(usb_clk),

			ResetSignal('sync').eq(~self.locked),
			ResetSignal('usb_io').eq(~self.locked),
			ResetSignal('usb').eq(~self.locked),
		]

		return m

class EnumValue(Enum):
	Foo = 0
	Bar = 1
	Baz = 2
	Qux = 3

class Top(Elaboratable):
	def __init__(self) -> None:
		counter_val = int(48 // 10)
		# Handful of sample signals for the ILA
		self.pll_locked = Signal()
		self.timer      = Signal(range(counter_val), reset = counter_val - 1, decoder = EnumValue)
		self.flops      = Signal(range(8), reset = 1)
		self.other      = Signal(8)

		# Create a USB-Based ILA
		self.ila = USBIntegratedLogicAnalyzer(
			# The initial set of signals we care about
			signals = [
				self.pll_locked,
				self.timer,
				self.flops,
				self.other,
			],
			# How many samples we want to capture
			sample_depth = 32,
			# How fast our sample domain is, in this case `sync`
			sample_rate  = 48e6,
			# The name of the USB resource to pull from the platform.
			bus = 'usb',
		)


	def elaborate(self, platform: ICEBreakerBitsyPlatform) -> Module:
		m = Module()

		# Status LEDs
		led_r = platform.request('led_r', dir = 'o')
		led_g = platform.request('led_g', dir = 'o')

		m.submodules.pll = pll = PLL()

		# Add the ILA so we actually build it
		m.submodules.ila = self.ila

		wiggle = Signal()
		woggle = Signal()

		# Add some "Private" signals to the ILA
		self.ila.append_signals([wiggle, woggle])

		with m.FSM(name = 'meow') as f:
			self.ila.add_fsm(f)

			with m.State('IDLE'):
				with m.If(self.flops[1]):
					m.next = 'WIGGLE'

			with m.State('WIGGLE'):
				m.d.sync += [
					wiggle.eq(self.timer[0]),
					woggle.eq(~wiggle),
				]

				with m.If(self.flops[2]):
					m.next = 'IDLE'

		# Dummy logic wiggles
		with m.If(self.timer == 0):
			m.d.sync += [
				self.timer.eq(self.timer.reset),
				self.flops.eq(self.flops.rotate_left(1)),
			]
			with m.If(self.flops[2]):
				m.d.sync += [ self.other.inc(), ]

		with m.Else():
			m.d.sync += [ self.timer.eq(self.timer - 1), ]


		with m.If(self.other[7]):
			m.d.comb += [ self.ila.trigger.eq(1) ]

		# Glue for the PLL and LEDs
		m.d.comb += [
			self.pll_locked.eq(pll.locked),
			led_r.eq(self.ila.sampling),
			led_g.eq(self.ila.complete),
		]

		return m


def main() -> int:
	top      = Top()
	vcd_file = Path.cwd() / 'bitsy_usb_ila.vcd'
	plat     = ICEBreakerBitsyPlatform()

	print('Building gateware...')
	try:
		plat.build(
			top, name = 'bitsy_usb_ila', do_program = True,
			script_after_read = 'scratchpad -copy abc9.script.flow3 abc9.script\n',
			synth_opts = ['-abc9'],
			nextpnr_opts = [ '--seed 1' ]
		)
	except CalledProcessError as e:
		# dfu-util complains because we don't come back as a DFU device
		# In that case we don't care there was an error
		if e.returncode != 251:
			raise e


	print('ILA Info:')
	print(f'  bytes per sample: {top.ila.bytes_per_sample}')
	print(f'  bits per sample:  {top.ila.bits_per_sample}')
	print(f'  sample rate:      {top.ila.sample_rate / 1e6} MHz')
	print(f'  sample period:    {top.ila.sample_period / 1e-9} ns')
	# Get the backhaul interface from the ILA module
	backhaul = top.ila.get_backhaul()
	print('Collecting ILA Samples')
	for ts, sample in backhaul.enumerate():
		print(f'{ts / 1e-9:.2f} ns:')
		for name, val in sample.items():
			print(f'  {name}: {val}')
	print(f'Writing to VCD: {vcd_file}')
	backhaul.write_vcd(vcd_file)

	return 0


if __name__ == '__main__':
	raise SystemExit(main())
