# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>

import sys
from pathlib       import Path


from torii         import Elaboratable, Module, Signal
from torii.sim     import Settle
from torii.test    import ToriiTestCase

try:
	from torii_ila.uart  import UARTIntegratedLogicAnalyzer
	from torii_ila._cobs import decode_rcobs
except ImportError:
	torii_ila_path = Path(__file__).resolve().parent

	if (torii_ila_path.parent / 'torii_ila').is_dir():
		sys.path.insert(0, str(torii_ila_path.parent))

	from torii_ila.uart  import UARTIntegratedLogicAnalyzer
	from torii_ila._cobs import decode_rcobs


a = Signal()
b = Signal(3)
c = Signal(8)
d = Signal(16)

uart_tx = Signal()

class UARTILADut(Elaboratable):
	def __init__(self) -> None:
		self.ila = UARTIntegratedLogicAnalyzer(
			divisor = 1,
			tx = uart_tx,
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
			byte |= (yield uart_tx) << idx
			yield Settle()
			yield
		# Read stop bit
		self.assertEqual((yield uart_tx), 1)
		yield

		return byte

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
			yield from self.step(512)


		sig_gen(self)
		ila(self)
		ingest_uart(self)


if __name__ == '__main__':
	from unittest import main
	main()
