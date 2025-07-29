# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Rachel Mant <git@dragonmux.network>
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>c

import sys
from pathlib       import Path
from typing        import Iterable
from enum          import Enum

from torii.hdl.ast import Signal
from torii.hdl.dsl import Module
from torii.hdl.ir  import Elaboratable
from torii.test    import ToriiTestCase
from torii.hdl.rec import Record, Direction

from usb_construct.types import (
	USBRequestRecipient, USBRequestType, USBStandardRequests, USBPacketID, LanguageIDs
)

try:
	from torii_ila.usb import USBIntegratedLogicAnalyzer
except ImportError:
	torii_ila_path = Path(__file__).resolve().parent

	if (torii_ila_path.parent / 'torii_ila').is_dir():
		sys.path.insert(0, str(torii_ila_path.parent))

	from torii_ila.usb import USBIntegratedLogicAnalyzer

class EnumValue(Enum):
	Foo = 0
	Bar = 1
	Baz = 2
	Qux = 3

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

		self.trig = Signal()
		counter_val = int(48 // 10)
		self.pll_locked = Signal()
		self.timer      = Signal(range(counter_val), reset = counter_val - 1, decoder = EnumValue)
		self.flops      = Signal(range(8), reset = 1)
		self.other      = Signal(8)

		self.ila = USBIntegratedLogicAnalyzer(
			# The initial set of signals we care about
			signals = [
				self.pll_locked,
				self.timer,
				self.flops,
				self.other,
			],
			# How many samples we want to capture
			sample_depth = 20,
			bus          = ('usb', 0)
		)

		self.d_p = Signal()
		self.d_n = Signal()

	def elaborate(self, platform) -> Module:
		m = Module()
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

		with m.If(self.other[2] & ~self.trig):
			m.d.sync += [ self.trig.eq(1), ]
			m.d.comb += [ self.ila.trigger.eq(1) ]

		return m

class USBILAOverflowTests(ToriiTestCase):
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

		self.assertEqual(self.dut.ila.bits_per_sample, 24)
		self.assertEqual(self.dut.ila.bytes_per_sample, 3)

		@ToriiTestCase.sync_domain(domain = 'usb')
		def usb(self: USBILAOverflowTests):
			yield
			yield from self.usb_sof()
			yield from self.usb_set_addr(ADDR)
			yield from self.usb_set_config(ADDR, 1)
			yield from self.wait_until_high(self.dut.ila.complete)
			yield from self.step(50)
			yield from self.usb_recv_ep_data(ADDR, 1, (
				0x0e, 0x01, 0x00,
				0x0c, 0x01, 0x00,
				0x0a, 0x01, 0x00,
				0x08, 0x01, 0x00,
				0x16, 0x01, 0x00,
				0x14, 0x01, 0x00,
				0x12, 0x01, 0x00,
				0x10, 0x01, 0x00,
				0x26, 0x01, 0x00,
				0x24, 0x01, 0x00,
				0x22, 0x01, 0x00,
				0x20, 0x01, 0x00,
				0x4e, 0x01, 0x00,
				0x4c, 0x01, 0x00,
				0x4a, 0x01, 0x00,
				0x48, 0x01, 0x00,
				0x56, 0x01, 0x00,
				0x54, 0x01, 0x00,
				0x52, 0x01, 0x00,
				0x50, 0x01, 0x00
			))
			yield from self.step(10)

		@ToriiTestCase.sync_domain(domain = 'sync')
		def ila(self: USBILAOverflowTests):
			yield

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
			crc = USBILAOverflowTests.crc16(byte, 8, crc)
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
		yield from self.wait_until_high(UTMI_BUS.tx_valid, timeout = 150)
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
