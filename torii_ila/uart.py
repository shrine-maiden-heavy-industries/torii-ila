# SPDX-License-Identifier: BSD-3-Clause

'''
UART Based ILA and backhaul interface.

'''

from collections.abc        import Iterable, Generator
from itertools              import chain, islice
from typing                 import Self

from torii                  import Cat, DomainRenamer, Elaboratable, Module, Signal
from torii.hdl.dsl          import FSM
from torii.lib.stdio.serial import AsyncSerialTX

from serial                 import Serial

from .ila                   import StreamILA
from .backhaul              import ILABackhaulInterface
from ._bits                 import bits
from ._cobs                 import RCOBSEncoder, decode_rcobs


__all__ = (
	'UARTIntegratedLogicAnalyzerBackhaul',
	'UARTIntegratedLogicAnalyzer',
)

# TODO(aki): We should probably have a transaction sync-word, that way we can re-sync mid ILA stream
#            for a continuous transaction.

class UARTIntegratedLogicAnalyzerBackhaul(ILABackhaulInterface):
	'''
	UART-based ILA backhaul interface, used in combination with :py:class:`UARTIntegratedLogicAnalyzer`
	to automatically set up a communications channel to get ILA samples off-device.

	An instance of this class is typically created by calling :py:meth:`UARTIntegratedLogicAnalyzer.get_backhaul`
	which lets the ILA configure the backhaul as needed.

	Alternatively you can pass the :py:class:`UARTIntegratedLogicAnalyzer` instance from the gateware
	to the constructor of this module.

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
		sample_width = self.ila.bytes_per_sample

		for idx in range(0, len(samples), sample_width):
			sample_raw = samples[idx:idx + sample_width]
			sample_len = len(Cat(self.ila._signals))

			yield bits.from_bytes(sample_raw, sample_len)

	def _ingest_samples(self: Self) -> Iterable[bits]:
		sample_width  = self.ila.bytes_per_sample
		total_samples = self.ila.sample_depth * sample_width

		def _batch(data: bytes):
			itr = iter(data)
			while (chunk := tuple(islice(itr, sample_width))):
				yield chunk

		# TODO(aki): We still need to figure out how to deal with the firehose if we start
		#            capturing in the middle.
		#
		#            There are two things we can possibly do:
		#            	1. Read until we hit the EOF marker, then read again to the next marker,
		#                  then throw away the first read as it may have been partial
		#               2. Have a lockout so the ILA will only send data when requested, and prevent
		#                  re-triggering when the UART is still sending data.
		#
		#            I'm not sure which is the best option tbh.

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

	Parameters
	----------
	divisor : int
		The clock divisor needed on the output domain to reach the desired baudrate.

	tx : Signal
		The UART Transmit signal to use.

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
		divisor: int, tx: Signal,
		# ILA Settings
		signals: Iterable[Signal] = list(), sample_depth: int = 32, sampling_domain: str = 'sync',
		sample_rate: float = 60e6, prologue_samples: int = 1,
	) -> None:
		self._domain = sampling_domain

		self.divisor = divisor
		self.tx      = tx
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
		m.submodules.uart  = uart  = AsyncSerialTX(divisor = self.divisor)

		data     = Signal.like(ila.stream.payload)
		to_send  = Signal(range(ila.bytes_per_sample + 1))
		finalize = Signal()

		m.d.comb += [
			self.tx.eq(uart.o),
			# Glue the rCOBS encoder to the UARTs face
			rcobs.raw.eq(data[0:8]),
			uart.data.eq(rcobs.enc),
			uart.ack.eq(rcobs.vld),
			rcobs.ack.eq(uart.rdy),
		]

		with m.FSM() as fsm:
			m.d.comb += [ self.idle.eq(fsm.ongoing('IDLE')), ]

			with m.State('IDLE'):
				m.d.comb += [ ila.stream.ready.eq(1), ]

				with m.If(ila.stream.valid):
					m.d.sync += [
						data.eq(ila.stream.payload),
						to_send.eq(ila.bytes_per_sample - 1),
					]
					m.d.comb += [ rcobs.strb.eq(1), ]

					m.next = 'TRANSMIT'

			with m.State('TRANSMIT'):
				# Wait for the rCOBS encoder to tell us to advance
				with m.If(rcobs.rdy):
					# If we still have bytes to send, shift over and send the next one
					with m.If(to_send > 0):
						m.d.comb += [ rcobs.strb.eq(1), ]
						m.d.sync += [
							to_send.eq(to_send - 1),
							data.eq(data[8:]),
						]
					# Otherwise, wrap up
					with m.Else():
						m.d.comb += [ ila.stream.ready.eq(1), ]

						# In the case where the stream has data to be slurped out, do so for the next byte
						with m.If(ila.stream.valid):
							m.d.sync += [
								data.eq(ila.stream.payload),
								to_send.eq(ila.bytes_per_sample - 1),
							]
						with m.Elif(finalize):
							m.d.sync += [ finalize.eq(0), ]
							m.next = 'FLUSH'
						with m.Else():
							with m.If(ila.stream.last):
								m.d.sync += [ finalize.eq(1), ]
							m.next = 'IDLE'

			with m.State('FLUSH'):
				with m.If(rcobs.rdy):
					m.d.comb += [ rcobs.finish.eq(1), ]
					m.next = 'FRAME'

			with m.State('FRAME'):
				# Let the rCOBS encoder settle and wait for the UART to become ready so we can
				# emit our framing byte
				with m.If(uart.rdy & rcobs.rdy):
					m.d.comb += [
						uart.data.eq(0x00),
						uart.ack.eq(1),
					]
					m.next = 'IDLE'

		# Fix up the lock domain, if needed
		if self._domain != 'sync':
			m = DomainRenamer({'sync': self._domain})(m)

		return m
