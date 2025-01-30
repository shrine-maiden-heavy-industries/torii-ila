# SPDX-License-Identifier: BSD-3-Clause

'''
USB Based ILA and backhaul interface.

'''

import time
from collections.abc                            import Generator, Iterable
from typing                                     import Self

from torii                                      import Cat, Elaboratable, Module, Signal
from torii.build.plat                           import Platform

from usb_construct.emitters                     import DeviceDescriptorCollection
from sol_usb.gateware.usb.usb2.device           import USBDevice
from sol_usb.gateware.usb.usb2.endpoints.stream import USBMultibyteStreamInEndpoint

import usb

from .ila                                       import StreamILA
from .backhaul                                  import ILABackhaulInterface
from ._bits                                     import bits

__all__ = (
	'USBIntegratedLogicAnalyzerBackhaul',
	'USBIntegratedLogicAnalyzer',
)


class USBIntegratedLogicAnalyzerBackhaul(ILABackhaulInterface):
	'''
	USB-based ILA backhaul interface, used in combination with :py:class:`USBIntegratedLogicAnalyzer`
	to automatically set up a communications channel to get ILA samples off-device.

	An instance of this class is typically created by calling :py:meth:`USBIntegratedLogicAnalyzer.get_backhaul`
	which lets the ILA configure the backhaul as needed.

	Alternatively you can pass the :py:class:`USBIntegratedLogicAnalyzer` instance from the gateware
	to the constructor of this module.

	See :py:class:`torii_ila.backhaul.ILABackhaulInterface` for public API.

	Parameters
	----------
	ila : USBIntegratedLogicAnalyzer
		The ILA being used.

	delay : int
		The number of second to delay the attempt to connect to the USB device, to allow for enumeration.

	'''

	def __init__(self: Self, ila: 'USBIntegratedLogicAnalyzer', delay: int = 3) -> None:
		super().__init__(ila)

		if delay > 0:
			time.sleep(delay)

		self._device = usb.core.find(idVendor = self.ila.USB_VID, idProduct = self.ila.USB_PID)

	def _split_samples(self: Self, samples: bytes) -> Generator[bits]:
		'''
		Splits the raw ingested bytes from the interface into a ``bits`` object,
		clipping the padding.
		'''

		sample_width = self.ila.bytes_per_sample

		for idx in range(0, len(samples), sample_width):
			sample_raw = samples[idx:idx + sample_width]
			sample_len = len(Cat(self.ila._signals))

			yield bits.from_bytes(sample_raw, sample_len)

	def _ingest_samples(self: Self) -> Iterable[bits]:
		''' Collect samples from the USB bulk endpoint. '''
		sample_width  = self.ila.bytes_per_sample
		total_samples = self.ila.sample_depth * sample_width

		# BUG(aki): We drain the full sample buffer all at once, which, while fine for smaller
		#           capture depths might be a problem for wide/deep captures.
		samples = self._device.read(0x80 | self.ila.BULK_EP_NUM, total_samples, timeout = 0)
		return list(self._split_samples(samples))



class USBIntegratedLogicAnalyzer(Elaboratable):
	'''
	A simple ILA that produces samples over a USB bulk endpoint.

	This shows up as a USB device with VID:PID of ``04A0:ACA7`` on the host with the Product string
	of ``Torii ILA`` and the Serial Number string of ``000000000``.

	Parameters
	----------
	signals : Iterable[torii.Signal]
		The signals to capture with the ILA.
		(default: list())

	sample_depth : int
		Number of samples we wish to capture.
		(default: 32)

	sampling_domain : str
		The clock domain the ILA sampling will take place on.
		(default: sync)

	sample_rate : float
		The outwards facing sample rate used for formatting output. This should be tied
		to the ``sampling_domain``'s frequency if possible.
		(default: 60e6 i.e 60MHz)

	prologue_samples : int
		The number of samples to capture **before** the trigger.
		(default: 1)

	bus : str | tuple[str, int] | None
		The USB Bus resource to use.
		(default: None)

	delayed_connect : bool
		Delay connection of the USB device.
		(default: False)

	max_pkt_size : int
		Max packet size.
		(default: 512)

	Attributes
	----------
	ila : StreamILA
		The inner ILA module used for actually ingesting the sample data.

	sample_width : int
		The width of the sample vector in bits.

	sample_depth : int
		The depth of the ILA sample buffer in samples.

	sample_rate : float
		The outwards facing sample rate used for formatting output

	sample_period : float
		The period of time between samples in nanoseconds, equivalent to ``1 / sample_rate``.

	bits_per_sample : int
		The nearest power of 2 number of bits per sample.

	bytes_per_sample : int
		The number of whole bytes per sample.

	trigger : Signal, in
		ILA Sample start trigger strobe.

	sampling : Signal, out
		Indicates when the ILA is actively sampling.

	complete : Signal, out
		Indicates when sampling is completed and the buffer is full.

	BULK_EP_NUM : int
		The fixed USB Bulk Endpoint number for the SOL USB Device.
		Value is set to ``1``.

	USB_VID : int
		The fixed USB Vendor ID for the SOL USB Device.
		Value is set to ``0x04A0``.

	USB_PID : int
		The fixed USB Product ID for the SOL USB Device.
		Value is set to ``0xACA7``.
	'''

	BULK_EP_NUM = 1

	# TODO(aki): Replace VID/PID when we get our hands on a proper set
	USB_VID = 0x04A0 # DEC
	USB_PID = 0xACA7 # A CAT :3

	_backhaul: USBIntegratedLogicAnalyzerBackhaul | None = None

	def get_backhaul(self: Self) -> USBIntegratedLogicAnalyzerBackhaul:
		'''
		Automatically construct a :py:class:`USBIntegratedLogicAnalyzerBackhaul` from this ILA
		instance.

		Returns
		-------
		USBIntegratedLogicAnalyzerBackhaul
			The newly constructed backhaul interface or the already constructed instance.
		'''

		if self._backhaul is None:
			self._backhaul = USBIntegratedLogicAnalyzerBackhaul(self)
		return self._backhaul

	def __init__(
		self: Self, *,
		# ILA Settings
		signals: Iterable[Signal] = list(), sample_depth: int = 32, sampling_domain: str = 'sync',
		sample_rate: float = 60e6, prologue_samples: int = 1,
		# USB Device Settings
		bus: str | tuple[str, int] | None = None, delayed_connect: bool = False, max_pkt_size: int = 512,
	) -> None:

		self._bus             = bus
		self._delayed_connect = delayed_connect
		self._max_pkt_size    = max_pkt_size

		self.ila = StreamILA(
			signals          = signals,
			sample_depth     = sample_depth,
			sampling_domain  = sampling_domain,
			sample_rate      = sample_rate,
			prologue_samples = prologue_samples,
			output_domain    = 'usb',
		)

		self._signals         = self.ila._signals
		self.sample_width     = self.ila.sample_width
		self.sample_depth     = self.ila.sample_depth
		self.sample_rate      = self.ila.sample_rate
		self.sample_period    = self.ila.sample_period
		self.bits_per_sample  = self.ila.bits_per_sample
		self.bytes_per_sample = self.ila.bytes_per_sample

		self.trigger  = self.ila.trigger
		self.sampling = self.ila.sampling
		self.complete = self.ila.complete

	def add_signal(self: Self, sig: Signal) -> None:
		'''
		Add a signal to the ILA capture list.

		This can be used to internal module signals to the ILA, or
		add signals after construction.

		Note
		----
		This method **must not** be called post elaboration, as we are unable to adjust
		the sample memory size after is it made concrete.

		Parameters
		----------
		sig : torii.Signal
			The signal to add to the ILA capture list.

		Raises
		------
		RuntimeError
			If called during the elaboration of the ILA module
		'''

		self.ila.add_signal(sig)

	def append_signals(self: Self, signals: Iterable[Signal]) -> None:
		'''
		Like :py:meth:`add_signal` but allows for adding an array of signals to the ILA capture list.

		Note
		----
		This method **must not** be called post elaboration, as we are unable to adjust
		the sample memory size after is it made concrete.

		Parameters
		----------
		signals : Iterable[torii.Signal]
			The list of additional signals to capture with the ILA.

		Raises
		------
		RuntimeError
			If called during the elaboration of the ILA module
		'''

		self.ila.append_signals(signals)

	def _make_descriptors(self: Self) -> DeviceDescriptorCollection:
		desc = DeviceDescriptorCollection()

		with desc.DeviceDescriptor() as dev:
			dev.idVendor  = self.USB_VID
			dev.idProduct = self.USB_PID

			dev.iManufacturer = ''
			dev.iProduct      = 'Torii ILA'
			dev.iSerialNumber = '000000000'

			dev.bNumConfigurations = 1

		with desc.ConfigurationDescriptor() as cfg:
			with cfg.InterfaceDescriptor() as iface:
				iface.bInterfaceNumber = 0

				with iface.EndpointDescriptor() as ep:
					ep.bEndpointAddress = 0x80 | self.BULK_EP_NUM
					ep.wMaxPacketSize   = self._max_pkt_size

		return desc


	def elaborate(self: Self, platform: Platform) -> Module:
		m = Module()

		m.submodules.ila = ila = self.ila

		if self._bus is not None:
			if isinstance(self._bus, str):
				usb_bus = platform.request(self._bus)
			elif isinstance(self._bus, tuple) and len(self._bus) == 2:
				usb_bus = platform.request(self._bus[0], self._bus[1])
		else:
			usb_bus = platform.request('usb')

		m.submodules.usb = usb = USBDevice(bus = usb_bus)

		descriptors = self._make_descriptors()
		usb.add_standard_control_endpoint(descriptors)

		stream_ep = USBMultibyteStreamInEndpoint(
			endpoint_number = self.BULK_EP_NUM,
			max_packet_size = self._max_pkt_size,
			byte_width      = self.bytes_per_sample
		)
		usb.add_endpoint(stream_ep)

		connect = Signal()

		# If we are delaying connection until the ILA is stuffed, wait, otherwise connect right away.
		if self._delayed_connect:
			with m.If(self.complete):
				m.d.usb += [ connect.eq(1), ]
		else:
			m.d.comb += [ connect.eq(1), ]


		# Bolt the streams together and hook up the connection signal.
		m.d.comb += [
			stream_ep.stream.stream_eq(ila.stream),
			usb.connect.eq(connect),
		]

		return m
