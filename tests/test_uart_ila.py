# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>

from torii.hdl.ast         import Signal
from torii.hdl.dsl         import Module
from torii.hdl.ir          import Elaboratable
from torii.lib.coding.cobs import decode_rcobs
from torii.sim             import Settle
from torii.test            import ToriiTestCase

from torii_ila.uart        import UARTILACommand, UARTIntegratedLogicAnalyzer

a = Signal()
b = Signal(3)
c = Signal(8)
d = Signal(16)

uart_tx = Signal()
uart_rx = Signal(reset = 1)

class UARTILADut(Elaboratable):
	def __init__(self) -> None:
		self.ila = UARTIntegratedLogicAnalyzer(
			divisor = 16,
			tx = uart_tx, rx = uart_rx,
			signals = [
				a, b, c, d
			],
			sample_depth    = 4,
			sampling_domain = 'sync',
			sample_rate     = 80e6,
		)

	def elaborate(self, platform) -> Module:
		m = Module()

		m.submodules.ila = self.ila

		return m

class UARTILATests(ToriiTestCase):
	dut: UARTILADut = UARTILADut
	dut_args = {}
	domains = (('sync', 48e6), )

	def uart_read_byte(self):
		# Wait for Start bit
		yield from self.wait_until_low(uart_tx)
		yield
		byte = 0
		# Read in byte
		for idx in range(8):
			yield from self.step(16)
			byte |= (yield uart_tx) << idx
		# Read stop bit
		yield from self.step(16)
		self.assertEqual((yield uart_tx), 1)

		return byte

	def uart_write_byte(self, byte: int):
		# Write the start bit
		yield uart_rx.eq(0)
		yield from self.step(16)
		# Data bits
		for idx in range(8):
			yield uart_rx.eq(byte >> idx)
			yield from self.step(16)
		# Stop bits
		yield uart_rx.eq(1)
		yield from self.step(16)

	@ToriiTestCase.simulation
	def test_capture(self):
		self.assertEqual(self.dut.ila.bits_per_sample, 32)
		self.assertEqual(self.dut.ila.bytes_per_sample, 4)

		@ToriiTestCase.sync_domain(domain = 'sync')
		def sig_gen(self: UARTILATests):
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
		def ingest_uart(self: UARTILATests):
			data = bytearray()
			while True:
				byte = (yield from self.uart_read_byte())
				if byte == 0x00:
					break
				data.append(byte)

			self.assertEqual(
				data,
				b'\xf1\x2e\x03\x01\xe2\x4e\x03\x01\xd5\x8e\x03\x01\xc6\x0e\x01\x04\x01'
			)
			self.assertEqual(
				decode_rcobs(data),
				b'\xf1\x2e\x00\x00\xe2\x4e\x00\x00\xd5\x8e\x00\x00\xc6\x0e\x01\x00'
			)

		@ToriiTestCase.sync_domain(domain = 'sync')
		def ila(self: UARTILATests):
			yield from self.step(16)
			yield self.dut.ila.trigger.eq(1)
			yield
			yield self.dut.ila.trigger.eq(0)
			yield Settle()
			yield
			yield from self.wait_until_high(self.dut.ila.complete)
			yield Settle()
			yield
			yield from self.step(512)
			yield from self.uart_write_byte(UARTILACommand.FLUSH)

		sig_gen(self)
		ila(self)
		ingest_uart(self)
