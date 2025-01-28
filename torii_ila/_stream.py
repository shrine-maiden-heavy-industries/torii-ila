# SPDX-License-Identifier: BSD-3-Clause
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


	def attach(self, iface: 'StreamInterface', omit):
		''' '''

		rhs = ('valid', 'first', 'last', 'payload', )
		lhs = ('ready', )
		att = [
			*[ iface[field].eq(self[field]) for field in rhs ],
			*[ self[field].eq(iface[field]) for field in lhs ],
		]

		return att

	def stream_eq(self, iface: 'StreamInterface', omit):
		'''  '''
		return iface.attach(self, omit)
