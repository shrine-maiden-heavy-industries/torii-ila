# SPDX-License-Identifier: BSD-3-Clause
# SPDX-FileCopyrightText: 2020 Great Scott Gadgets <info@greatscottgadgets.com>
# SPDX-FileCopyrightText: 2025 Aki Van Ness <aki@lethalbit.net>

# This file is adapted from SOL and is only used for compatibility with it,
# It can be removed once Torii gets a sane stream impl internally and SOL is
# ported to use that.

from torii import Signal, Record

__all__ = (
	'StreamInterface',
)

class StreamInterface(Record):
	'''
	A very simple record implementing a unidirectional stream interface.

	Parameters
	----------
	data_width : int
		Stream width in bits.

	Attributes
	----------
	ready : Signal, recv
		Indicates that the receiver will accept the data at the next active
		clock edge.

	first : Signal, send
		Indicates that the data is the first of the current packet.

	last : Signal, send
		Indicates that the data is the last of the current packet.

	payload : Signal(data_width), send
		The data to be transmitted.

	valid : Signal(valid_width), send
		Indicates  ``data`` is part of this transfer.

	'''

	valid: Signal
	ready: Signal
	first: Signal
	last: Signal
	payload: Signal

	def __init__(self, data_width: int = 8, valid_width: int = 1) -> None:
		super().__init__([
			('payload',  data_width),
			('valid', valid_width),
			('first', 1),
			('last',  1),
			('ready', 1)
		])


	def attach(self, iface: 'StreamInterface', omit: set = set()):
		'''
		Attach to a target stream.

		This method connects our ``valid``, ``first``, ``last``, and ``data`` fields to
		the downstream facing ``stream``, and their ``ready`` field to ours.

		This establishes a connection to where we are the originating stream, and ``stream``
		is the receiving stream.

		.. code-block::

			self.data  -> stream.data
			self.valid -> stream.valid
			self.first -> stream.first
			self.last  -> stream.last
			self.ready <- stream.ready

		Parameters
		----------
		stream : torii_ila._stream.StreamInterface
			The stream we are attaching to.

		omit : set[str]
			A set of additional stream fields to exclude from the tap connection.
			(default: {})
		'''

		rhs = ('valid', 'first', 'last', 'payload', )
		lhs = ('ready', )
		att = [
			*[ iface[field].eq(self[field]) for field in rhs if field not in omit ],
			*[ self[field].eq(iface[field]) for field in lhs if field not in omit ],
		]

		return att

	def stream_eq(self, iface: 'StreamInterface', omit: set = set()):
		'''
		Receive from target stream.

		This method connects the ``valid``, ``first``, ``last``, and ``data`` from ``stream`` to ours,
		and our ``ready`` field to theirs.

		This establishes a connection to where ``stream`` is the originating stream, and we are the receiving
		stream.

		.. code-block::

			self.data  <- stream.data
			self.valid <- stream.valid
			self.first <- stream.first
			self.last  <- stream.last
			self.ready -> stream.ready

		This function is effectively the inverse of :py:meth:`attach`, in fact, it's implementation
		is just:

		.. code-block:: python

			stream.attach(self, ...)

		It is provided as a more logical way to connect streams.

		Parameters
		----------
		stream : torii_ila._stream.StreamInterface
			The stream to attach to this stream.

		omit : set[str]
			A set of additional stream fields to exclude from the tap connection.
			(default: {})
		'''
		return iface.attach(self, omit)
