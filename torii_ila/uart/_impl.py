# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>

'''
UART Based ILA and backhaul interface.

'''

from collections.abc        import Generator, Iterable
from enum                   import IntEnum, unique
from itertools              import chain, islice
from typing                 import Self

from serial                 import Serial

from torii.hdl.ast          import Cat, Signal
from torii.hdl.dsl          import FSM, Module
from torii.hdl.ir           import Elaboratable
from torii.hdl.xfrm         import DomainRenamer
from torii.lib.coding.cobs  import RCOBSEncoder, decode_rcobs
from torii.lib.stdio.serial import AsyncSerial

from .._bits                import bits
from ..backhaul             import ILABackhaulInterface
from ..ila                  import StreamILA

__all__ = (
	'UARTILACommand',
	'UARTIntegratedLogicAnalyzerBackhaul',
	'UARTIntegratedLogicAnalyzer',
)

@unique
class UARTILACommand(IntEnum):
	''' These are commands the UART ILA knows about '''

	NONE   = 0x00
	''' No command '''
	FLUSH  = 0x01
	''' Flush the ILA Sample memory down the UART. '''
	STREAM = 0x02
	''' Send the ILA sample memory down the UART until ``UARTILACommand.STOP`` is sent. '''
	STOP   = 0x03
	''' Stop the ILA from sending sample stream down the UART. '''

class UARTIntegratedLogicAnalyzerBackhaul(ILABackhaulInterface['UARTIntegratedLogicAnalyzer']):
	'''
	UART-based ILA backhaul interface, used in combination with :py:class:`UARTIntegratedLogicAnalyzer`
	to automatically set up a communications channel to get ILA samples off-device.

	An instance of this class is typically created by calling :py:meth:`UARTIntegratedLogicAnalyzer.get_backhaul`
	which lets the ILA configure the backhaul as needed.

	Alternatively you can pass the :py:class:`UARTIntegratedLogicAnalyzer` instance from the gateware
	to the constructor of this module.

	The data coming off the ILA is `rCOBS <https://github.com/Dirbaio/rcobs>`_ encoded and the samples are
	byte-wise swizzled, we automatically decode and de-swizzle the samples.

	See :py:class:`torii_ila.backhaul.ILABackhaulInterface` for public API.

	Parameters
	----------
	ila : UARTIntegratedLogicAnalyzer
		The ILA being used.

	serial : Serial
		The serial port the ILA is connected over.

	'''

	def __init__(self: Self, ila: 'UARTIntegratedLogicAnalyzer', serial: Serial) -> None:
		super().__init__(ila)

		self._port = serial
		self._port.reset_input_buffer()

	def _split_samples(self: Self, samples: bytes) -> Generator[bits]:
		'''
		Split the raw sample data stream into a stream of bit-vectors.

		Parameters
		----------
		samples : bytes
			The ILA sample data to be split.

		Returns
		-------
		Generator[torii.ila._bits.bits]
			Stream of samples as appropriately sized bit-vectors.
		'''

		sample_width = self.ila.bytes_per_sample

		for idx in range(0, len(samples), sample_width):
			sample_raw = samples[idx:idx + sample_width]
			sample_len = len(Cat(self.ila._signals))

			yield bits.from_bytes(sample_raw, sample_len)

	def _ingest_samples(self: Self) -> Iterable[bits]:
		'''
		Collect samples from the ILA backhaul interface.

		In the case of the UART backhaul interface, we read until we hit an
		EOF marker, then rCOBS decode and then de-swizzle the samples.

		Those are then transformed into bit-vectors with the padding truncated.

		Returns
		-------
		Iterable[torii_ila._bits.bits]
			Collection of sample bit-vectors.
		'''

		sample_width  = self.ila.bytes_per_sample
		total_samples = self.ila.sample_depth * sample_width

		def _batch(data: bytes):
			itr = iter(data)
			while (chunk := tuple(islice(itr, sample_width))):
				yield chunk

		self._port.write(UARTILACommand.FLUSH.to_bytes(length = 1))

		# Consume up to the EOF marker
		raw = self._port.read_until(b'\x00')
		# Decode the rCOBS samples up to the \x00 byte
		decoded_samples = decode_rcobs(raw[0:total_samples + 1])
		# The samples from the UART come in byte-reversed, so we need to swap them then flatten to bytes
		samples = bytes(chain.from_iterable((samp[::1] for samp in _batch(decoded_samples))))
		# Split the decoded and fixed samples
		return list(self._split_samples(samples))

class UARTIntegratedLogicAnalyzer(Elaboratable):
	'''
	A simple ILA that dumps sample memory down a UART pipe.

	The configuration is 8n1 at the baud dictated by the divisor, which should
	be ``int(clk // baud)`` for the desired baud rate.

	The output data from this ILA is an `rCOBS <https://github.com/Dirbaio/rcobs>`_ encoded byte
	stream with a ``0x00`` :abbr:`EOF (End Of Frame)` marker indicating the end of an ILA capture
	sample buffer.

	Due to the way the UART works, each sample is byte-reversed, meaning the LSB is output first, then
	bytes up to the MSB. The :py:class:`UARTIntegratedLogicAnalyzerBackhaul` deals with all of the
	implementation details, meaning the samples that come out from it are already rCOBS decoded and
	swizzled back into the correct order.


	Parameters
	----------
	divisor : int
		The clock divisor needed on the output domain to reach the desired baudrate.

	tx : Signal
		The UART Transmit signal to use.

	rx : Signal
		The UART Receive signal to use.

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
		(default: ``50e6`` i.e ``50MHz``)

	prologue_samples : int
		The number of samples to capture **before** the trigger.
		(default: 1)

	Attributes
	----------
	domain : str
		The domain the ILA is sampling on.

	ila : IntegratedLogicAnalyzer
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

	idle : Signal, out
		Indicates the UART transmitter is sitting idle and is ready to send data.
	'''

	_backhaul: UARTIntegratedLogicAnalyzerBackhaul | None = None

	def get_backhaul(self: Self, port: Serial) -> UARTIntegratedLogicAnalyzerBackhaul:
		'''
		Automatically create a :py:class:`UARTIntegratedLogicAnalyzerBackhaul` from this ILA
		instance.

		Parameters
		----------
		port : serial.Serial
			The serial port to use to ingest data from.

		Returns
		-------
		UARTIntegratedLogicAnalyzerBackhaul
			The newly constructed backhaul interface or the already constructed instance.
		'''

		if self._backhaul is None:
			self._backhaul = UARTIntegratedLogicAnalyzerBackhaul(self, port)
		return self._backhaul

	@property
	def sample_width(self) -> int:
		return self.ila.sample_width

	@property
	def bits_per_sample(self) -> int:
		return self.ila.bits_per_sample

	@property
	def bytes_per_sample(self) -> int:
		return self.ila.bytes_per_sample

	def __init__(
		self: Self, *,
		# UART Settings
		divisor: int, tx: Signal, rx: Signal,
		# ILA Settings
		signals: Iterable[Signal] = list(), sample_depth: int = 32, sampling_domain: str = 'sync',
		sample_rate: float = 50e6, prologue_samples: int = 1,
	) -> None:
		self._domain = sampling_domain

		self.divisor = divisor
		self.tx      = tx
		self.rx      = rx
		self.idle    = Signal()

		self.ila = StreamILA(
			signals          = signals,
			sample_depth     = sample_depth,
			sampling_domain  = 'sync', # We stuff this through a `DomainRenamer` later
			sample_rate      = sample_rate,
			prologue_samples = prologue_samples
		)

		self._signals         = self.ila._signals
		self.sample_depth     = self.ila.sample_depth
		self.sample_rate      = self.ila.sample_rate
		self.sample_period    = self.ila.sample_period

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

	def add_fsm(self: Self, fsm: FSM) -> None:
		'''
		Add a Torii FSM state to the ILA.

		.. code-block:: python

			with m.FSM(name = 'Thing') as fsm:
				ila.add_fsm(fsm)


		This is effectively equivalent to:

		.. code-block:: python

			with m.FSM(name = 'Thing') as fsm:
				ila.add_signal(fsm.state)

		Note
		----
		The FSM you add to the ILA should be named, as to prevent name collisions.

		Note
		----
		This method **must not** be called post elaboration, as we are unable to adjust
		the sample memory size after is it made concrete.

		Parameters
		----------
		fsm : torii.hdl.dsl.FSM
			The FSM to add to the ILA.

		Raises
		------
		RuntimeError
			If called during the elaboration of the ILA module
		'''

		self.ila.add_fsm(fsm)

	def elaborate(self: Self, _) -> Module:
		m = Module()

		m.submodules.ila   = ila   = self.ila
		m.submodules.rcobs = rcobs = RCOBSEncoder()
		m.submodules.uart  = uart  = AsyncSerial(divisor = self.divisor)

		data_tx  = Signal.like(ila.stream.data)
		data_rx  = Signal.like(uart.rx.data, decoder = UARTILACommand)
		to_send  = Signal(range(ila.bytes_per_sample + 1))
		finalize = Signal()
		send     = Signal()
		stream   = Signal()

		m.d.comb += [
			# Connect the UART
			self.tx.eq(uart.tx.o),
			uart.rx.i.eq(self.rx),
			# Glue the rCOBS encoder to the UARTs face
			rcobs.raw.eq(data_tx[0:8]),
			uart.tx.data.eq(rcobs.enc),
			uart.tx.ack.eq(rcobs.valid),
			rcobs.ack.eq(uart.tx.rdy),

		]

		with m.FSM(name = 'rx') as fsm:
			m.d.comb += [ uart.rx.start.eq(fsm.ongoing('IDLE')), ]

			with m.State('IDLE'):
				with m.If(uart.rx.done):
					m.d.sync += [ data_rx.eq(uart.rx.data), ]
					m.next = 'CMD'

			with m.State('CMD'):
				with m.Switch(data_rx):
					with m.Case(UARTILACommand.FLUSH):
						m.d.sync += [ send.eq(1), ]
					with m.Case(UARTILACommand.STREAM):
						m.d.sync += [
							send.eq(1),
							stream.eq(1),
						]
					with m.Case(UARTILACommand.STOP):
						m.d.sync += [ stream.eq(0), ]

				m.d.sync += [ data_rx.eq(0), ]
				m.next = 'IDLE'

		with m.FSM(name = 'tx') as fsm:
			m.d.comb += [ self.idle.eq(fsm.ongoing('IDLE')), ]

			with m.State('IDLE'):
				m.d.comb += [ ila.stream.ready.eq(send), ]

				with m.If(ila.stream.valid & send):
					m.d.sync += [
						data_tx.eq(ila.stream.data),
						to_send.eq(ila.bytes_per_sample - 1),
					]
					# If we're coming out of idle we need to strobe the rCOBS encode to latch
					m.d.comb += [ rcobs.strobe.eq(1), ]

					m.next = 'TRANSMIT'

			with m.State('TRANSMIT'):
				# Wait for the rCOBS encoder to tell us to advance
				with m.If(rcobs.ready):
					# If we still have bytes to send, shift over and send the next one
					with m.If(to_send > 0):
						# Tell the rCOBS encoder that data is valid
						m.d.comb += [ rcobs.strobe.eq(1), ]

						m.d.sync += [
							to_send.eq(to_send - 1),
							data_tx.eq(data_tx[8:]),
						]
					# Otherwise, wrap up
					with m.Else():
						m.d.comb += [ ila.stream.ready.eq(1), ]

						# In the case where the stream has data to be slurped out, do so for the next byte
						with m.If(ila.stream.valid):
							m.d.sync += [
								data_tx.eq(ila.stream.data),
								to_send.eq(ila.bytes_per_sample - 1),
							]
						with m.Elif(finalize):
							# We just got done with the last transfer, flush the state and end the frame
							m.d.sync += [ finalize.eq(0), ]
							m.next = 'FLUSH'
						with m.Else():
							# If we are about to hit the last bit of the stream, we need to tell
							# the rCOBS encoder to finalize at the end of the next transfer.
							with m.If(ila.stream.last):
								m.d.sync += [ finalize.eq(1), ]
							m.next = 'IDLE'

			with m.State('FLUSH'):
				# Wait for the rCOBS encoder to become ready, then tell it to wrap up
				with m.If(rcobs.ready):
					m.d.comb += [ rcobs.finish.eq(1), ]
					m.next = 'FRAME'

			with m.State('FRAME'):
				# Let the rCOBS encoder settle and wait for the UART to become ready so we can
				# emit our framing byte
				with m.If(uart.tx.rdy & rcobs.ready):
					m.d.comb += [
						uart.tx.data.eq(0x00),
						uart.tx.ack.eq(1),
					]
					with m.If(~stream):
						m.d.sync += [ send.eq(0), ]
					m.next = 'IDLE'

		# Fix up the lock domain, if needed
		if self._domain != 'sync':
			m = DomainRenamer(sync = self._domain)(m)

		return m
