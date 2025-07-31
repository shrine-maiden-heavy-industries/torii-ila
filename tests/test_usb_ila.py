# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Rachel Mant <git@dragonmux.network>
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>c

import sys
from pathlib             import Path
from typing              import Iterable

from torii.hdl.ast       import Signal
from torii.hdl.dsl       import Module
from torii.hdl.ir        import Elaboratable
from torii.sim           import Settle
from torii.test          import ToriiTestCase
from torii.hdl.rec       import Record, Direction

from usb_construct.types import USBStandardRequests, USBPacketID

try:
	from torii_ila.usb import USBIntegratedLogicAnalyzer
except ImportError:
	torii_ila_path = Path(__file__).resolve().parent

	if (torii_ila_path.parent / 'torii_ila').is_dir():
		sys.path.insert(0, str(torii_ila_path.parent))

	from torii_ila.usb import USBIntegratedLogicAnalyzer

a = Signal()
b = Signal(3)
c = Signal(8)
d = Signal(16)

UTMI_BUS = Record([
	# Send interface
	('tx_data', 8, Direction.FANOUT),
	('tx_valid', 1, Direction.FANOUT),
	('tx_ready', 1, Direction.FANIN),
	# Receive interface
	('rx_data', 8, Direction.FANIN),
	('rx_valid', 1, Direction.FANIN),
	('rx_active', 1, Direction.FANIN),

	# Control signals
	('line_state', 2),
	('vbus_valid', 1),
	('session_valid', 1),
	('session_end', 1),
	('rx_error', 1),
	('host_disconnect', 1),
	('id_digital', 1),
	('xcvr_select', 2),
	('term_select', 1),
	('op_mode', 2),
	('suspend', 1),
	('id_pullup', 1),
	('dm_pulldown', 1),
	('dp_pulldown', 1),
	('chrg_vbus', 1),
	('dischrg_vbus', 1),
	('use_external_vbus_indicator', 1),
])

class Platform():
	device = 'TEST'

	def request(self, name: str, number: int = 0):
		assert name == 'usb'
		assert number == 0
		return UTMI_BUS

class USBILADut(Elaboratable):
	def __init__(self) -> None:
		self.ila = USBIntegratedLogicAnalyzer(
			signals = [
				a, b, c, d
			],
			sample_depth    = 4,
			sampling_domain = 'sync',
			sample_rate     = 80e6,
			bus             = ('usb', 0)
		)

		self.d_p = Signal()
		self.d_n = Signal()

	def elaborate(self, platform) -> Module:
		m = Module()
		m.submodules.ila = self.ila
		return m

class USBILATests(ToriiTestCase):
	dut: USBILADut = USBILADut
	dut_args = {}
	domains = (('usb', 60e6), ('sync', 60e6))
	platform = Platform()

	_last_frame: int = 0
	_last_data_send: USBPacketID | None = None
	_last_data_recv: USBPacketID | None = None

	@ToriiTestCase.simulation
	def test_capture(self):
		ADDR = 0x1a

		self.assertEqual(self.dut.ila.bits_per_sample, 32)
		self.assertEqual(self.dut.ila.bytes_per_sample, 4)

		@ToriiTestCase.sync_domain(domain = 'sync')
		def sig_gen(self: USBILATests):
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

		@ToriiTestCase.sync_domain(domain = 'usb')
		def usb(self: USBILATests):
			# Tell the reset sequencer engine that the bus is active
			yield UTMI_BUS.vbus_valid.eq(1)
			# And in a valid non-SE0 state (we don't care which,
			# we just don't want the reset sequencer doing bad things)
			yield UTMI_BUS.line_state.eq(0b01)
			yield
			yield from self.usb_sof()
			yield from self.usb_set_addr(ADDR)
			yield from self.usb_set_config(ADDR, 1)
			yield from self.usb_recv_ep_data(ADDR, 1, (
				0xf1, 0x2e, 0x00, 0x00,
				0xe2, 0x4e, 0x00, 0x00,
				0xd5, 0x8e, 0x00, 0x00,
				0xc6, 0x0e, 0x01, 0x00,
			))
			yield from self.usb_recv_ep_data(ADDR, 1, (
				0xf1, 0x2d, 0x00, 0x00,
				0xe2, 0x4d, 0x00, 0x00,
				0xd5, 0x8d, 0x00, 0x00,
				0xc6, 0x0d, 0x01, 0x00,
			))
			yield from self.usb_recv_ep_data(ADDR, 1, (
				0xf1, 0x2c, 0x00, 0x00,
				0xe2, 0x4c, 0x00, 0x00,
				0xd5, 0x8c, 0x00, 0x00,
				0xc6, 0x0c, 0x01, 0x00,
			))
			yield from self.usb_recv_ep_data(ADDR, 1, (
				0xf1, 0x2b, 0x00, 0x00,
				0xe2, 0x4b, 0x00, 0x00,
				0xd5, 0x8b, 0x00, 0x00,
				0xc6, 0x0b, 0x01, 0x00,
			))
			yield from self.usb_recv_ep_data(ADDR, 1, (
				0xf1, 0x2a, 0x00, 0x00,
				0xe2, 0x4a, 0x00, 0x00,
				0xd5, 0x8a, 0x00, 0x00,
				0xc6, 0x0a, 0x01, 0x00,
			))
			yield from self.step(10)

		@ToriiTestCase.sync_domain(domain = 'sync')
		def ila(self: USBILATests):
			# Run the LA through a trigger sequence on 10 points to get enough data to entirely fill the LA
			# front-end and start dropping captures
			while (yield c) != 0xf0:
				yield
			yield from self.pulse(self.dut.ila.trigger, post_step = False)
			while (yield c) != 0xe8:
				yield
			yield from self.pulse(self.dut.ila.trigger, post_step = False)
			while (yield c) != 0xe0:
				yield
			yield from self.pulse(self.dut.ila.trigger, post_step = False)
			while (yield c) != 0xd8:
				yield
			yield from self.pulse(self.dut.ila.trigger, post_step = False)
			while (yield c) != 0xd0:
				yield
			yield from self.pulse(self.dut.ila.trigger, post_step = False)
			while (yield c) != 0xc8:
				yield
			yield from self.pulse(self.dut.ila.trigger, post_step = False)
			while (yield c) != 0xc0:
				yield
			yield from self.pulse(self.dut.ila.trigger, post_step = False)
			while (yield c) != 0xb8:
				yield
			yield from self.pulse(self.dut.ila.trigger, post_step = False)
			while (yield c) != 0xb0:
				yield
			yield from self.pulse(self.dut.ila.trigger, post_step = False)
			while (yield c) != 0xa8:
				yield
			yield from self.pulse(self.dut.ila.trigger, post_step = False)

		sig_gen(self)
		usb(self)
		ila(self)

	@staticmethod
	def crc5(data: int, bit_len: int) -> int:
		crc = 0x1f

		for bit_idx in range(bit_len):
			bit = (data >> bit_idx) & 1
			crc <<= 1

			if bit != (crc >> 5):
				crc ^= 0x25
			crc &= 0x1f

		crc ^= 0x1f
		return int(f'{crc:05b}'[::-1], base = 2)

	@staticmethod
	def crc16(data: int, bit_len: int, crc_in: int = 0) -> int:
		crc = int(f'{crc_in ^ 0xffff:016b}'[::-1], base = 2)

		for bit_idx in range(bit_len):
			bit = (data >> bit_idx) & 1
			crc <<= 1

			if bit != (crc >> 16):
				crc ^= 0x18005
			crc &= 0xffff

		crc ^= 0xffff
		return int(f'{crc:016b}'[::-1], base = 2)

	@staticmethod
	def crc16_buff(data: Iterable[int]) -> int:
		crc = 0
		for byte in data:
			crc = USBILATests.crc16(byte, 8, crc)
		return crc

	def usb_send_control_token(self, pid: USBPacketID, token_data: int):
		frame = token_data | (self.crc5(token_data, 11) << 11)
		yield UTMI_BUS.rx_active.eq(1)
		yield
		yield UTMI_BUS.rx_valid.eq(1)
		yield UTMI_BUS.rx_data.eq(pid.byte())
		yield
		yield UTMI_BUS.rx_data.eq(frame & 0xff)
		yield
		yield UTMI_BUS.rx_data.eq(frame >> 8)
		yield
		yield UTMI_BUS.rx_valid.eq(0)
		yield UTMI_BUS.rx_active.eq(0)
		yield

	def usb_consume_response(self, data: Iterable[int]):
		yield UTMI_BUS.tx_ready.eq(1)
		yield
		yield from self.wait_until_high(UTMI_BUS.tx_valid, timeout = 50)
		for byte in data:
			self.assertEqual((yield UTMI_BUS.tx_valid), 1)
			self.assertEqual((yield UTMI_BUS.tx_data), byte)
			yield
		self.assertEqual((yield UTMI_BUS.tx_valid), 0)
		yield UTMI_BUS.tx_ready.eq(0)

	def usb_sof(self):
		yield from self.usb_send_control_token(USBPacketID.SOF, self._last_frame)
		self._last_frame += 1
		self._last_frame &= 0x7ff

	def usb_solicit(self, addr: int, ep: int, pid: USBPacketID):
		yield from self.usb_send_control_token(pid, addr | (ep << 7))

	def usb_in(self, addr: int, ep: int):
		yield from self.usb_solicit(addr, ep, USBPacketID.IN)

	def usb_out(self, addr: int, ep: int):
		yield from self.usb_solicit(addr, ep, USBPacketID.OUT)

	def usb_setup(self, addr: int):
		self._last_data_send = None
		yield from self.usb_solicit(addr, 0, USBPacketID.SETUP)

	def usb_send_ack(self):
		yield UTMI_BUS.rx_active.eq(1)
		yield
		yield UTMI_BUS.rx_valid.eq(1)
		yield UTMI_BUS.rx_data.eq(USBPacketID.ACK.byte())
		yield
		yield UTMI_BUS.rx_valid.eq(0)
		yield UTMI_BUS.rx_active.eq(0)
		yield

	def usb_recv_ack(self):
		yield from self.usb_consume_response((USBPacketID.ACK.byte(),))

	def usb_recv_stall(self):
		yield from self.usb_consume_response((USBPacketID.STALL.byte(),))

	def usb_send_data(self, data: Iterable[int]):
		if self._last_data_send is None or self._last_data_send == USBPacketID.DATA1:
			self._last_data_send = USBPacketID.DATA0
		else:
			self._last_data_send = USBPacketID.DATA1

		yield UTMI_BUS.rx_active.eq(1)
		yield
		yield UTMI_BUS.rx_valid.eq(1)
		yield UTMI_BUS.rx_data.eq(self._last_data_send.byte())
		yield
		crc = 0
		for byte in data:
			crc = self.crc16(byte, 8, crc)
			yield UTMI_BUS.rx_data.eq(byte)
			yield
		yield UTMI_BUS.rx_data.eq(crc & 0xff)
		yield
		yield UTMI_BUS.rx_data.eq(crc >> 8)
		yield
		yield UTMI_BUS.rx_valid.eq(0)
		yield UTMI_BUS.rx_active.eq(0)
		yield

	def usb_recv_zlp(self):
		yield from self.usb_consume_response((USBPacketID.DATA1.byte(), 0x00, 0x00))

	def usb_send_zlp(self):
		yield from self.usb_send_data(())

	def usb_send_setup_packet(self, addr: int, data: Iterable[int]):
		yield from self.usb_setup(addr)
		yield from self.usb_send_data(data)
		yield from self.usb_recv_ack()

	def usb_set_addr(self, addr: int):
		yield from self.usb_send_setup_packet(0, (
			0x00, USBStandardRequests.SET_ADDRESS,
			*addr.to_bytes(2, byteorder = 'little'), 0x00, 0x00, 0x00, 0x00
		))
		yield from self.usb_in(0, 0)
		yield from self.usb_recv_zlp()
		yield from self.usb_send_ack()

	def usb_set_config(self, addr: int, config: int):
		yield from self.usb_send_setup_packet(addr, (
			0x00, USBStandardRequests.SET_CONFIGURATION,
			*config.to_bytes(2, byteorder = 'little'), 0x00, 0x00, 0x00, 0x00
		))
		yield from self.usb_in(addr, 0)
		yield from self.usb_recv_zlp()
		yield from self.usb_send_ack()

	def usb_set_interface(self, addr: int, interface: int, alt: int):
		yield from self.usb_send_setup_packet(addr, (
			0x01, USBStandardRequests.SET_INTERFACE,
			*alt.to_bytes(2, byteorder = 'little'),
			*interface.to_bytes(2, byteorder = 'little'),
			0x00, 0x00
		))
		yield from self.usb_in(addr, 0)
		yield from self.usb_recv_zlp()
		yield from self.usb_send_ack()

	def usb_recv_ep_data(self, addr: int, ep: int, data: Iterable[int]):
		if self._last_data_recv is None or self._last_data_recv == USBPacketID.DATA1:
			self._last_data_recv = USBPacketID.DATA0
		else:
			self._last_data_recv = USBPacketID.DATA1

		crc = self.crc16_buff(data)
		yield from self.usb_in(addr, ep)
		yield from self.usb_consume_response((
			self._last_data_recv.byte(), *data, *crc.to_bytes(2, byteorder = 'little')
		))
		yield from self.usb_send_ack()

if __name__ == '__main__':
	from unittest import main
	main()
