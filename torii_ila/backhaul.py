# SPDX-License-Identifier: BSD-3-Clause

from abc             import ABCMeta, abstractmethod
from collections.abc import Callable, Generator, Iterable
from typing          import TypeAlias, Self, TYPE_CHECKING
from pathlib         import Path


from vcd             import VCDWriter
from vcd.common      import VarType as VCDVarType
from vcd.writer      import Variable as VCDVar

from .ila            import IntegratedLogicAnalyzer
from ._bits          import bits

if TYPE_CHECKING:
	from .usb  import USBIntegratedLogicAnalyzer
	from .uart import UARTIntegratedLogicAnalyzer

__all__ = (
	'ILABackhaulInterface',
)

ILAInterface: TypeAlias = 'IntegratedLogicAnalyzer | USBIntegratedLogicAnalyzer | UARTIntegratedLogicAnalyzer'
Sample: TypeAlias = dict[str, bits]
Samples: TypeAlias = Iterable[Sample]

# TODO(aki): We should probably provide a way to have a live, firehose-like stream output for the backhaul interfaces
#            it's a little more useful with the UART interface, as the USB interface is capable of doing batching mostly
#            by itself already.
class ILABackhaulInterface(metaclass = ABCMeta):
	'''
	This represents the API for all ILA backhaul interfaces to implement.


	Backhaul interfaces primarily deal with `Sample`s, which are `dict`s that map
	signal names to :py:class:`torii_ila._bits.bits`

	Parameters
	----------
	ila : IntegratedLogicAnalyzer
		The ILA to interface to.

	Attributes
	----------
	ila : IntegratedLogicAnalyzer
		The instance of the ILA used on the device. This is used to allow the backhaul
		to automatically configure itself appropriately and also know what signals are being
		captures and the like.

	samples : Iterable[dict[str, bytes]] | None
		The collected samples from the ILA.
	'''

	def __init__(self: Self, ila: ILAInterface) -> None:
		self.ila = ila
		self.samples: Samples | None = None

	@abstractmethod
	def _ingest_samples(self: Self) -> Iterable[bits]:
		''' Acquire ILA samples from the backhaul interface. '''

		raise NotImplementedError('ILA backhaul interfaces must implement this method')

	def _parse_sample(self, raw: bits) -> Sample:
		'''
		Parse the raw sample into a dictionary that maps signal name to value.

		Parameters
		----------
		raw : bits
			The raw binary sample extracted out of the backhaul interface.

		Returns
		-------
		dict[str, bits]
			Signal name to value mapping

		'''

		pos = 0
		sample: Sample = dict()

		# BUG(aki): This *might* not be 100% stable if the signal orders shift around under us.
		for sig in self.ila._signals:
			#
			width = len(sig)
			bits  = raw[pos : (pos + width)]
			# Advance to the next signal
			pos += width

			sample[sig.name] = bits

		return sample

	def _parse_samples(self, raw: Iterable[bytes]) -> Samples:
		''' Parse all given samples '''

		return [ self._parse_sample(sample) for sample in raw ]

	def refresh(self: Self) -> None:
		''' Update the internal sample buffer with samples ingested from the backhaul interface. '''

		self.samples = self._parse_samples(self._ingest_samples())

	def enumerate(self: Self) -> Generator[tuple[float, Sample]]:
		'''
		Iterate over all of the samples received from our backhaul interface.

		Returns timestamp, sample pairs.
		'''

		# BUG(aki): This assumes that `refresh()` will always populate the sample buffer, this
		#           is not correct, and may cause issues.
		if self.samples is None:
			self.refresh()

		ts: float = 0

		for sample in self.samples:
			yield ts, sample
			ts += self.ila.sample_period

	def write_vcd(self: Self, vcd_file: Path, inject_sample_clock: bool = True, post_step: int = 1) -> None:
		'''
		Dump all received ILA samples from the backhaul interface into a VCD file on disk.s

		Parameters
		----------
		vcd_file : Path
			The file to write to.

		inject_sample_clock : bool
			Add a clock that is timed to the ILA sample clock.
			(default: True)

		post_step : int
			The number of post-sample steps to append to the VCD. This is used
			so the last sample value is actually displayed as a transition.

			This option is only meaningful if ``inject_sample_clock`` is true, as
			we can't advance the VCD without it.
			(default: 1)
		'''

		with vcd_file.open('w') as vcd_stream:
			with VCDWriter(vcd_stream, timescale = '1 ns', comment = 'Torii ILA Dump') as writer:
				# Signal mapping
				vcd_signals: dict[str, VCDVar] = dict()
				sig_decoder: dict[str, Callable[[int], str]] = dict()

				# If we are adding a matched clock from the ILA then set that up
				if inject_sample_clock:
					clk_value: int = 1
					clk_time: int  = 0
					clk_signal     = writer.register_var(
						'ila', 'ila_clk', VCDVarType.wire, size = 1, init = clk_value ^ 1
					)

				for sig in self.ila._signals:
					if sig.decoder is not None:
						sig_decoder[sig.name] = sig.decoder
						vcd_signals[sig.name] = writer.register_var(
							'ila', sig.name, VCDVarType.string, size = 1,
							init = sig_decoder[sig.name](sig.reset).expandtabs().replace(' ', '_')
						)
					else:
						vcd_signals[sig.name] = writer.register_var(
							'ila', sig.name, VCDVarType.wire, size = len(sig), init = sig.reset
						)

				last_ts: float = 0.0
				# Wiggle out our captured samples
				for ts, sample in self.enumerate():
					last_ts = ts
					# If we are injecting our sample clock, make sure we run it up to the time
					# of the last sample before we add a new sample
					if inject_sample_clock:
						while clk_time < ts:
							writer.change(clk_signal, clk_time / 1e-9, clk_value)
							clk_value ^= 1 # Tick the clock
							clk_time += (self.ila.sample_period / 2)

					# Iterate over the un-packed sample
					for name, value in sample.items():
						if (decoder := sig_decoder.get(name)) is not None:
							decoded_val = decoder(value.to_int()).expandtabs().replace(' ', '_')
							writer.change(vcd_signals[name], ts / 1e-9, decoded_val)
						else:
							writer.change(vcd_signals[name], ts / 1e-9, value.to_int())

				# Append any needed post-steps, but only if we have a sample clock to tick
				if inject_sample_clock:
					for _ in range(post_step):
						# Advance time
						last_ts += self.ila.sample_period
						while clk_time < last_ts:
							writer.change(clk_signal, clk_time / 1e-9, clk_value)
							clk_value ^= 1
							clk_time += (self.ila.sample_period / 2)
