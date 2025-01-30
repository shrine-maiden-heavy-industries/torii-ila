# USB-Based Integrated Logic Analyzer

This module provides the ILA as a streaming USB device, for use with the [USB backhaul] interface. It does this by wrapping the {py:class}`StreamILA <torii_ila.ila.StreamILA>` and providing the output stream of the ILA capture data as a USB device using the [SOL] {py:class}`USBMultibyteStreamInEndpoint <sol_usb.gateware.usb.usb2.endpoints.stream s.USBMultibyteStreamInEndpoint>`

```{eval-rst}
.. autoclass:: torii_ila.usb.USBIntegratedLogicAnalyzer
  :members:
```

[USB backhaul]: ../backhaul/usb.md
[SOL]: https://github.com/shrine-maiden-heavy-industries/sol
