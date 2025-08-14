# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>

from torii.hdl.ast import Signal
from torii.hdl.dsl import Module
from torii.hdl.ir  import Elaboratable
from torii.sim     import Settle
from torii.test    import ToriiTestCase

from torii_ila.ila import IntegratedLogicAnalyzer

a = Signal()
b = Signal(3)
c = Signal(8)
d = Signal(16)

class ILADut(Elaboratable):
	def __init__(self) -> None:
		self.ila = IntegratedLogicAnalyzer(
			signals = [
				a, b, c, d
			],
			sample_depth    = 32,
			sampling_domain = 'sync',
			sample_rate     = 80e6
		)

		self.ila_mem = self.ila._sample_memory

	def elaborate(self, platform) -> Module:
		m = Module()

		m.submodules.ila = self.ila

		return m

class ILATests(ToriiTestCase):
	dut: ILADut = ILADut
	dut_args = {}
	domains = (('sync', 80e6), )

	@ToriiTestCase.simulation
	def test_capture(self):
		self.assertEqual(self.dut.ila.bits_per_sample, 32)
		self.assertEqual(self.dut.ila.bytes_per_sample, 4)

		@ToriiTestCase.sync_domain(domain = 'sync')
		def sig_gen(self: ILATests):
			yield d.eq(1)
			for i in range(64):
				yield Settle()
				yield
				yield a.eq(~a)
				yield b.eq(i & 0b0111)
				yield c.eq(~(i & 0b11111111))
				yield d.eq(d.rotate_left(1))
			yield Settle()
			yield

		@ToriiTestCase.sync_domain(domain = 'sync')
		def ila(self: ILATests):
			yield from self.step(16)
			yield self.dut.ila.trigger.eq(1)
			yield
			yield self.dut.ila.trigger.eq(0)
			yield Settle()
			yield
			self.assertEqual((yield self.dut.ila.trigger),  0)
			self.assertEqual((yield self.dut.ila.sampling), 1)
			self.assertEqual((yield self.dut.ila.complete), 0)
			yield from self.step(self.dut.ila.sample_depth)
			self.assertEqual((yield self.dut.ila.trigger),  0)
			self.assertEqual((yield self.dut.ila.sampling), 0)
			self.assertEqual((yield self.dut.ila.complete), 1)

		sig_gen(self)
		ila(self)
