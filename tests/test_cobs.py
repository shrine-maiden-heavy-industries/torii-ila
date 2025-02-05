# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>

import sys
from pathlib       import Path
from random        import randbytes

from torii.sim     import Settle
from torii.test    import ToriiTestCase

try:
	from torii_ila._cobs import RCOBSEncoder, decode_rcobs
except ImportError:
	torii_ila_path = Path(__file__).resolve().parent

	if (torii_ila_path.parent / 'torii_ila').is_dir():
		sys.path.insert(0, str(torii_ila_path.parent))

	from torii_ila._cobs import RCOBSEncoder, decode_rcobs


TEST_DATA = randbytes(512)


class RCOBSTests(ToriiTestCase):
	dut: RCOBSEncoder = RCOBSEncoder
	dut_args = {}
	domains = (('sync', 80e6), )

	@ToriiTestCase.simulation
	@ToriiTestCase.sync_domain(domain = 'sync')
	def test_encode(self):
		cobs_run = 0

		yield from self.step(5)

		for byte in TEST_DATA:
			cobs_run += 1

			yield from self.wait_until_high(self.dut.rdy)
			yield self.dut.raw.eq(byte)
			yield self.dut.strb.eq(1)
			yield Settle()
			yield
			yield self.dut.strb.eq(0)
			yield Settle()
			yield
			yield from self.wait_until_high(self.dut.vld)

			if byte == 0:
				self.assertEqual((yield self.dut.enc), cobs_run)
				cobs_run = 0
			else:
				if cobs_run == 254:
					cobs_run = 0
					self.assertEqual((yield self.dut.enc), 0xFF)
				else:
					self.assertEqual((yield self.dut.enc), byte)

			yield self.dut.ack.eq(1)
			yield Settle()
			yield
			yield self.dut.ack.eq(0)


		yield self.dut.finish.eq(1)
		yield Settle()
		yield
		yield Settle()
		yield
		yield self.dut.finish.eq(0)
		yield from self.wait_until_high(self.dut.vld)
		self.assertEqual((yield self.dut.enc), cobs_run + 1)

	def test_decode(self):
		test_vectors = [
			(b'\x01', b''),
			(b'\x01\x01', b'\x00'),
			(b'\x01\x01\x01', b'\x00\x00'),
			(b'\x11\x22\x03\x33\x02', b'\x11\x22\x00\x33'),
			(b'\x11\x02\x01\x01\x01', b'\x11\x00\x00\x00'),
			(b'\x11\x22\x33\x44\x05', b'\x11\x22\x33\x44'),
		]

		for encoded, decoded in test_vectors:
			self.assertEqual(decode_rcobs(encoded), decoded)


if __name__ == '__main__':
	from unittest import main
	main()
