# ILA Backhaul Interface

```{toctree}
:hidden:

uart
usb
```

In order to extract data off the device, Torii ILA uses whats called a "backhaul inteface". It's effectively an abstraction that is used to provide a consistent interface to interact with the ILA stream regardless if it's over [USB], [UART], or some other interface.

```{eval-rst}
.. autoclass:: torii_ila.backhaul.ILABackhaulInterface
  :members:
```

[USB]: ./usb.md
[UART]: ./uart.md
