# SPDX-License-Identifier: BSD-3-Clause

from typing         import Iterable, Self

from torii          import Cat, DomainRenamer, Elaboratable, Memory, Module, Signal
from torii.lib.cdc  import FFSynchronizer
from torii.lib.fifo import AsyncFIFOBuffered

from ._stream        import StreamInterface

__all__ = (
	'IntegratedLogicAnalyzer',
	'StreamILA',
)

class IntegratedLogicAnalyzer(Elaboratable):
	'''
	A simple Integrated Logic Analyzer for Torii.

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

	Attributes
	----------
	sample_width : int
		The width of the sample vector in bits.

	sample_depth : int
		The depth of the ILA sample buffer in samples.

	sample_rate : float
		The outwards facing sample rate used for formatting output

	sample_period : float
		``1 / sample_rate``

	prologue_samples : int
		The number of samples to retain prior to the ILA ``trigger`` signal going high.

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

	sample_index : Signal, in
		The sample the ILA will output.

	sample_capture : Signal, out
		The sample corresponding to the sample index.

	'''

	def __init__(
		self: Self, *,
		signals: Iterable[Signal] = list(), sample_depth: int = 32, sampling_domain: str = 'sync',
		sample_rate: float = 60e6, prologue_samples: int = 1
	) -> None:
		self._sampling_domain  = sampling_domain
		self._signals          = signals
		self._inputs           = Cat(*self._signals)
		self.sample_width      = len(self._inputs)
		self.sample_depth      = sample_depth
		self.prologue_samples  = prologue_samples
		self.sample_rate       = sample_rate
		self.sample_period     = 1 / sample_rate

		self.bits_per_sample = 2 ** ((self.sample_width - 1).bit_length())
		self.bytes_per_sample = (self.bits_per_sample + 7) // 8

		self._sample_memory    = Memory(
			width = self.sample_width, depth = sample_depth, name = 'ila_storage'
		)

		self.trigger  = Signal()
		self.sampling = Signal()
		self.complete = Signal()

		self.sample_index   = Signal(range(self.sample_depth + 1))
		self.sample_capture = Signal(self.sample_width)

	def elaborate(self: Self, _) -> Module:
		m = Module()

		m.submodules.write_port = wp = self._sample_memory.write_port()
		m.submodules.read_port  = rp = self._sample_memory.read_port(domain = 'sync')

		# Handle any prologue samples we need to capture
		if self.prologue_samples >= 2:
			inputs = Signal.like(self._inputs)
			m.submodules += FFSynchronizer(
				self._inputs, inputs, stages = self.prologue_samples
			)
		elif self.prologue_samples == 1:
			inputs = Signal.like(self._inputs)
			m.d.sync += [ inputs.eq(self._inputs), ]
		else:
			inputs = self._inputs

		write_pos = Signal(range(self.sample_depth))
		m.d.comb += [
			wp.data.eq(inputs),
			wp.addr.eq(write_pos),

			self.sample_capture.eq(rp.data),
			rp.addr.eq(self.sample_index),
		]

		# Ensure we're not carelessly writing into sample memory
		m.d.sync += [ wp.en.eq(0), ]

		with m.FSM(name = 'ILA') as fsm:
			# Assert we're sampling unless we're in the IDLE state
			m.d.comb += [ self.sampling.eq(~fsm.ongoing('IDLE')), ]

			# Waiting for sample trigger
			with m.State('IDLE'):
				with m.If(self.trigger):
					m.next = 'SAMPLE'

					# We will be late a cycle, so force a sample capture now
					m.d.sync += [
						wp.en.eq(1),
						write_pos.eq(0),
						self.complete.eq(0),
					]
			# Capture samples
			with m.State('SAMPLE'):
				# Keep sampling until we can't anymore
				m.d.sync += [
					wp.en.eq(1),
					write_pos.inc(),
				]

				# If we're on the last sample, then wrap up
				with m.If(write_pos + 1 == self.sample_depth):
					m.next = 'IDLE'

					m.d.sync += [
						self.complete.eq(1),
						wp.en.eq(0),
					]

		# Adjust our sampling domain appropriately
		if self._sampling_domain != 'sync':
			return DomainRenamer({'sync': self._sampling_domain})(m)

		return m

class StreamILA(Elaboratable):
	'''
	A simple implementation of a stream-based ILA for use in the the UART and USB ILA's.

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
		(default: 'sync')

	output_domain : str | None
		The clock domain the ILA stream will output on. If ``None`` it will be the same as ``sampling_domain``
		(default: None)

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
		``1 / sample_rate``

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

	stream : StreamInterface
		The output stream of ILA samples.
	'''

	def __init__(
		self: Self, *,
		signals: Iterable[Signal] = list(), sample_depth: int = 32, sampling_domain: str = 'sync',
		sample_rate: float = 60e6, prologue_samples: int = 1, output_domain: str | None = None
	) -> None:

		self.domain = sampling_domain

		if (o_domain := output_domain) is not None:
			self._o_domain = o_domain
		else:
			self._o_domain = self.domain

		self.ila = IntegratedLogicAnalyzer(
			signals          = signals,
			sample_depth     = sample_depth,
			sampling_domain  = 'sync',
			sample_rate      = sample_rate,
			prologue_samples = prologue_samples
		)

		self._signals         = self.ila._signals
		self.sample_width     = self.ila.sample_width
		self.sample_depth     = self.ila.sample_depth
		self.sample_rate      = self.ila.sample_rate
		self.sample_period    = self.ila.sample_period
		self.bits_per_sample  = self.ila.bits_per_sample
		self.bytes_per_sample = self.ila.bytes_per_sample

		self.trigger  = Signal()
		self.sampling = self.ila.sampling
		self.complete = self.ila.complete

		self.stream = StreamInterface(data_width = self.bits_per_sample)

	def elaborate(self: Self, _) -> Module:
		m = Module()

		m.submodules.ila = ila = self.ila

		if self._o_domain == self.domain:
			i_domain_stream = self.stream
		else:
			i_domain_stream = StreamInterface(data_width = self.bits_per_sample)

		curr_sample = Signal(range(ila.sample_depth))

		m.d.comb += [
			ila.sample_index.eq(curr_sample),
			i_domain_stream.payload.eq(ila.sample_capture),
		]

		with m.FSM(name = 'StreamILA'):
			with m.State('IDLE'):
				m.d.comb += [ self.ila.trigger.eq(self.trigger), ]

				with m.If(self.trigger):
					m.next = 'SAMPLING'

			with m.State('SAMPLING'):
				# Wait for the ILA to get done sampling
				with m.If(ila.complete):
					# Reset the current sample number and instruct the stream that we are
					# on the first bit of data
					m.d.sync += [
						curr_sample.eq(0),
						i_domain_stream.first.eq(1),
					]
					# and go to yeet the data over the wall
					m.next = 'SENDING'

			with m.State('SENDING'):
				# We have a valid buffer of samples, time to send them off

				data_valid = Signal(reset = 1)

				# Ensure the stream is always providing valid data while we are sending
				# and indicate if we are on the last sample.
				m.d.comb += [
					i_domain_stream.valid.eq(data_valid),
					i_domain_stream.last.eq(curr_sample == (self.sample_depth - 1)),
				]

				# Every time the downstream is ready, toss anew one at them
				with m.If(i_domain_stream.ready):
					with m.If(data_valid):
						m.d.sync += [
							curr_sample.inc(),
							data_valid.eq(0),
							i_domain_stream.first.eq(0),
						]

						with m.If(i_domain_stream.last):
							m.next = 'IDLE'
					with m.Else():
						m.d.sync += [ data_valid.eq(1), ]

		# Add the clock domain crossing machinery if we need to
		if self._o_domain != self.domain:
			i_domain_signals = Cat(
				i_domain_stream.first,
				i_domain_stream.payload,
				i_domain_stream.last,
			)

			o_domain_signals = Cat(
				self.stream.first,
				self.stream.payload,
				self.stream.last
			)

			m.submodules.cdc_fifo = fifo = AsyncFIFOBuffered(
				width    = len(i_domain_signals),
				depth    = 16,
				w_domain = 'sync',
				r_domain = self._o_domain,
			)

			m.d.comb += [
				# From the ILA sampling domain
				fifo.w_data.eq(i_domain_signals),
				fifo.w_en.eq(i_domain_stream.valid),
				i_domain_stream.ready.eq(fifo.w_rdy),

				# Onto the output domain
				o_domain_signals.eq(fifo.r_data),
				self.stream.valid.eq(fifo.r_rdy),
				fifo.r_en.eq(self.stream.ready),
			]

		# Adjust our domain appropriately
		if self.domain != 'sync':
			return DomainRenamer({'sync': self.domain})(m)

		return m
