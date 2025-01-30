# UART-Based Integrated Logic Analyzer

This module provides the ILA as a streaming UART device, for use with the [UART backhaul] interface. It does this by wrapping the {py:class}`StreamILA <torii_ila.ila.StreamILA>` and providing the output stream of the ILA capture data as a UART port using the [Torii] {py:class}`AsyncSerialTX <torii.lib.stdio.serial.AsyncSerialTX>`

The baud rate for the UART stream is adjustable, but the UART stream itself is fixed to `8n1`.

```{eval-rst}
.. autoclass:: torii_ila.uart.UARTIntegratedLogicAnalyzer
  :members:
```

[UART backhaul]: ../backhaul/uart.md
[Torii]: https://github.com/shrine-maiden-heavy-industries/torii-hdl
