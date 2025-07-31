# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>

import sys
from pathlib       import Path

from torii.hdl.ast import Signal
from torii.hdl.cd  import ClockDomain
from torii.hdl.dsl import Module
from torii.hdl.ir  import Elaboratable
from torii.sim     import Settle
from torii.test    import ToriiTestCase

try:
	from torii_ila import StreamILA
except ImportError:
	torii_ila_path = Path(__file__).resolve().parent

	if (torii_ila_path.parent / 'torii_ila').is_dir():
		sys.path.insert(0, str(torii_ila_path.parent))

	from torii_ila import StreamILA


a = Signal()
b = Signal(3)
c = Signal(8)
d = Signal(16)

class StreamILADut(Elaboratable):
	def __init__(self, o_domain: str) -> None:
		self.o_domain = o_domain
		self.ila = StreamILA(
			signals = [
				a, b, c, d
			],
			sample_depth    = 32,
			sampling_domain = 'sync',
			sample_rate     = 80e6,
			output_domain   = o_domain
		)

	def elaborate(self, platform) -> Module:
		m = Module()

		m.submodules.ila = self.ila

		if self.o_domain != 'sync':
			m.domains = ClockDomain(self.o_domain)

		return m

class StreamILASameDomainTests(ToriiTestCase):
	dut: StreamILADut = StreamILADut
	dut_args = {'o_domain': 'sync'}
	domains = (('sync', 80e6), )

	@ToriiTestCase.simulation
	def test_capture(self):
		self.assertEqual(self.dut.ila.bits_per_sample, 32)
		self.assertEqual(self.dut.ila.bytes_per_sample, 4)

		@ToriiTestCase.sync_domain(domain = 'sync')
		def sig_gen(self: StreamILASameDomainTests):
			yield d.eq(1)
			for i in range(128):
				yield Settle()
				yield
				yield a.eq(~a)
				yield b.eq(i & 0b0111)
				yield c.eq(~(i & 0b11111111))
				yield d.eq(d.rotate_left(1))
			yield Settle()
			yield

		@ToriiTestCase.sync_domain(domain = 'sync')
		def ila(self: StreamILASameDomainTests):
			yield from self.step(16)
			yield self.dut.ila.trigger.eq(1)
			yield
			yield self.dut.ila.trigger.eq(0)
			yield Settle()
			yield
			self.assertEqual((yield self.dut.ila.stream.valid), 0)
			self.assertEqual((yield self.dut.ila.stream.last), 0)
			self.assertEqual((yield self.dut.ila.stream.first), 0)

			self.assertEqual((yield self.dut.ila.trigger),  0)
			self.assertEqual((yield self.dut.ila.sampling), 1)
			self.assertEqual((yield self.dut.ila.complete), 0)
			yield from self.step(self.dut.ila.sample_depth)
			self.assertEqual((yield self.dut.ila.trigger),  0)
			self.assertEqual((yield self.dut.ila.sampling), 0)
			self.assertEqual((yield self.dut.ila.complete), 1)

		@ToriiTestCase.sync_domain(domain = 'sync')
		def stream_drain(self: StreamILASameDomainTests):
			yield from self.wait_until_high(self.dut.ila.stream.valid, timeout = 128)
			self.assertEqual((yield self.dut.ila.stream.first), 1)
			yield self.dut.ila.stream.ready.eq(1)
			yield Settle()
			yield
			for i in range(self.dut.ila.sample_depth):
				self.assertEqual((yield self.dut.ila.ila.sample_index), i)
				self.assertEqual((yield self.dut.ila.stream.valid), 1)
				yield Settle()
				yield
				self.assertEqual((yield self.dut.ila.stream.valid), 0)
				yield Settle()
				yield
				if i == self.dut.ila.sample_depth - 2:
					self.assertEqual((yield self.dut.ila.stream.last), 1)

			self.assertEqual((yield self.dut.ila.stream.valid), 0)
			self.assertEqual((yield self.dut.ila.stream.last), 0)
			self.assertEqual((yield self.dut.ila.stream.first), 0)

		stream_drain(self)
		sig_gen(self)
		ila(self)

if __name__ == '__main__':
	from unittest import main
	main()
