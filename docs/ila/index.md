# Integrated Logic Analyzers

```{toctree}
:hidden:

uart
usb
```

Torii ILA has two primary ILA modules, the {py:class}`IntegratedLogicAnalyzer <torii_ila.ila.IntegratedLogicAnalyzer>` and the {py:class}`StreamILA <torii_ila.ila.StreamILA>`.

{py:class}`IntegratedLogicAnalyzer <torii_ila.ila.IntegratedLogicAnalyzer>` is a very simple ILA capable of capturing samples from a Torii design and exposes a simple interface for accessing the sample memory.

{py:class}`StreamILA <torii_ila.ila.StreamILA>` wraps the {py:class}`IntegratedLogicAnalyzer <torii_ila.ila.IntegratedLogicAnalyzer>` in a stream API that allows for the [USB] an [UART] ILA modules to ingest the data in a streaming way.


```{eval-rst}
.. autoclass:: torii_ila.ila.IntegratedLogicAnalyzer
  :members:

.. autoclass:: torii_ila.ila.StreamILA
  :members:
```

These are used in conjunction with a [backhaul] interface to extract data off the device and on to the host system.

[USB]: ./usb.md
[UART]: ./uart.md
[backhaul]: ../backhaul/index.md
